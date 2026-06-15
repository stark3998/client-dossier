# backend/app/ingestion/pipeline.py
import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone

from app.config import get_settings
from app.ingestion.parser import parse_document, SUPPORTED_EXTENSIONS
from app.ingestion.chunker import chunk_document
from app.ingestion.embedder import embed_chunks
from app.models.source import IngestJob
from app.telemetry import track_event

logger = logging.getLogger(__name__)


async def run_ingestion(
    job: IngestJob,
    doc_index_repo,
    search_service,
    embedding_service,
    job_repo=None,
    analysis_service=None,
    force: bool = False,
):
    settings = get_settings()
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    if job_repo:
        await job_repo.upsert(job.model_dump(mode='json'))

    target_path = job.path or settings.ONEDRIVE_SYNC_PATH
    files = _discover_files(target_path)
    job.total_files = len(files)

    logger.info(
        "Ingestion started: %d files in %s (force=%s, concurrency=%d)",
        len(files), target_path, force, settings.INGEST_CONCURRENCY,
    )

    sem = asyncio.Semaphore(settings.INGEST_CONCURRENCY)
    lock = asyncio.Lock()

    async def process_file(file_path: str) -> None:
        async with sem:
            async with lock:
                job.active_files.append(file_path)
                if job_repo:
                    await job_repo.upsert(job.model_dump(mode='json'))

            result = None
            try:
                result = await _ingest_file(
                    file_path=file_path,
                    client_name=job.client_name or _infer_client_name(file_path, target_path),
                    doc_index_repo=doc_index_repo,
                    search_service=search_service,
                    embedding_service=embedding_service,
                    analysis_service=analysis_service,
                    force=force,
                )
            except Exception as e:
                logger.error("Failed to ingest %s: %s", file_path, e)
                track_event("ingestion.file.failed", {
                    "file_path": file_path, "error_message": str(e)
                })
                async with lock:
                    job.active_files = [f for f in job.active_files if f != file_path]
                    job.processed_files += 1
                    job.file_events = (job.file_events + [{
                        "file_name": os.path.basename(file_path),
                        "status": "error",
                        "error": str(e)[:120],
                    }])[-20:]
                    if job_repo:
                        await job_repo.upsert(job.model_dump(mode='json'))
                return

            async with lock:
                job.active_files = [f for f in job.active_files if f != file_path]
                job.processed_files += 1
                if not result["indexed"]:
                    job.skipped_files += 1
                else:
                    job.file_events = (job.file_events + [{
                        "file_name": os.path.basename(file_path),
                        "status": "done",
                        "chunks": result["chunks"],
                        "duration_ms": result["duration_ms"],
                    }])[-20:]
                if job_repo:
                    await job_repo.upsert(job.model_dump(mode='json'))

    try:
        await asyncio.gather(*[process_file(fp) for fp in files])
        job.status = "done"
    except Exception as e:
        job.status = "error"
        job.error = str(e)
        logger.error("Ingestion job failed: %s", e)
    finally:
        job.completed_at = datetime.now(timezone.utc)
        job.active_files = []
        if job_repo:
            await job_repo.upsert(job.model_dump(mode='json'))


async def _ingest_file(
    file_path: str,
    client_name: str,
    doc_index_repo,
    search_service,
    embedding_service,
    analysis_service=None,
    force: bool = False,
) -> dict:
    import time
    start = time.time()

    track_event("ingestion.file.started", {
        "file_path": file_path,
        "file_type": os.path.splitext(file_path)[1],
        "client_name": client_name,
    })

    # Hash check (I/O-bound, offloaded to thread)
    content_hash = await asyncio.to_thread(_file_hash, file_path)
    existing = await doc_index_repo.get(content_hash, file_path)
    if not force and existing and existing.get("content_hash") == content_hash:
        logger.info("Skipping unchanged file: %s", file_path)
        return {"indexed": False, "chunks": 0, "duration_ms": 0}

    # Parse (CPU-bound, offloaded to thread)
    parsed = await asyncio.to_thread(parse_document, file_path)

    # Run document analysis to extract metadata for chunk enrichment
    doc_type = None
    engagement_names: list[str] = []
    key_topics: list[str] = []
    document_date = None
    deliverable_related = False
    if analysis_service:
        try:
            analysis = await analysis_service.analyze_document(parsed, client_name)
            doc_type = analysis.doc_type
            engagement_names = analysis.engagement_references or []
            key_topics = analysis.key_topics or []
            if analysis.extracted_dates:
                date_strings = [d.date for d in analysis.extracted_dates if d.date]
                document_date = min(date_strings) if date_strings else None
            deliverable_related = doc_type in {
                "proposal", "contract", "report", "status_report"
            }
        except Exception as e:
            logger.warning("Analysis skipped for %s: %s", file_path, e)

    # Chunk (CPU-bound, offloaded to thread)
    chunks = await asyncio.to_thread(
        chunk_document,
        sections=parsed.sections,
        file_path=parsed.file_path,
        file_type=parsed.file_type,
        client_name=client_name,
        last_modified=parsed.last_modified,
        doc_type=doc_type,
        engagement_names=engagement_names,
        key_topics=key_topics,
        document_date=document_date,
        deliverable_related=deliverable_related,
    )

    if not chunks:
        logger.info("No chunks produced for: %s", file_path)
        return {"indexed": False, "chunks": 0, "duration_ms": int((time.time() - start) * 1000)}

    # Embed (async network I/O, with retry on rate limits)
    chunks = await embed_chunks(chunks, embedding_service)

    # Upsert to search index
    search_docs = []
    for chunk in chunks:
        search_docs.append({
            "id": chunk.id,
            "content": chunk.content,
            "content_vector": chunk.embedding,
            "file_path": chunk.metadata.file_path,
            "file_type": chunk.metadata.file_type,
            "section_title": chunk.metadata.section_title or "",
            "page_number": chunk.metadata.page_number,
            "client_name": chunk.metadata.client_name,
            "chunk_hash": chunk.chunk_hash,
            "last_modified": chunk.metadata.last_modified.isoformat(),
            "record_type": "document",
            "doc_type": chunk.metadata.doc_type or "",
            "engagement_names": chunk.metadata.engagement_names,
            "key_topics": chunk.metadata.key_topics,
            "document_date": chunk.metadata.document_date or "",
            "deliverable_related": chunk.metadata.deliverable_related,
        })
    await search_service.upsert_chunks(search_docs)

    # Track in Cosmos doc_index
    await doc_index_repo.upsert({
        "id": content_hash,
        "file_path": file_path,
        "file_type": parsed.file_type,
        "content_hash": content_hash,
        "chunk_count": len(chunks),
        "last_indexed": datetime.now(timezone.utc).isoformat(),
    })

    duration_ms = int((time.time() - start) * 1000)
    track_event("ingestion.file.completed", {
        "file_path": file_path,
        "chunk_count": len(chunks),
        "duration_ms": duration_ms,
    })
    logger.info("Ingested %s: %d chunks in %dms", file_path, len(chunks), duration_ms)
    return {"indexed": True, "chunks": len(chunks), "duration_ms": duration_ms}


def _discover_files(path: str) -> list[str]:
    files = []
    if os.path.isfile(path):
        if _is_indexable(path):
            files.append(path)
    elif os.path.isdir(path):
        for root, _, filenames in os.walk(path):
            for fname in filenames:
                full = os.path.join(root, fname)
                if _is_indexable(full):
                    files.append(full)
    return sorted(files)


def _is_indexable(file_path: str) -> bool:
    fname = os.path.basename(file_path)
    if fname.startswith("~$"):  # Office temp lock files
        return False
    if fname.startswith("."):   # Hidden files
        return False
    ext = os.path.splitext(fname)[1].lower()
    return ext in SUPPORTED_EXTENSIONS


def _infer_client_name(file_path: str, base_path: str) -> str:
    rel = os.path.relpath(file_path, base_path)
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 else "default"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()
