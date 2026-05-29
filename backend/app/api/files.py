# backend/app/api/files.py
import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks

from app.config import get_settings

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/tree")
async def file_tree(path: str = ""):
    settings = get_settings()
    base = settings.ONEDRIVE_SYNC_PATH
    target = os.path.join(base, path) if path else base

    if not os.path.isdir(target):
        raise HTTPException(status_code=404, detail="Directory not found")

    # Security: prevent path traversal
    target = os.path.realpath(target)
    base = os.path.realpath(base)
    if not target.startswith(base):
        raise HTTPException(status_code=403, detail="Access denied")

    return _build_tree(target, base)


@router.get("/preview")
async def file_preview(path: str, max_chars: int = 5000):
    settings = get_settings()
    full_path = os.path.join(settings.ONEDRIVE_SYNC_PATH, path)

    full_path = os.path.realpath(full_path)
    base = os.path.realpath(settings.ONEDRIVE_SYNC_PATH)
    if not full_path.startswith(base):
        raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        from app.ingestion.parser import parse_document
        parsed = parse_document(full_path)
        text = "\n\n".join(
            (f"## {s.title}\n{s.text}" if s.title else s.text)
            for s in parsed.sections
        )
        return {"path": path, "content": text[:max_chars], "truncated": len(text) > max_chars}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot parse file: {e}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    client_name: str = Form(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload a file for a client, auto-ingest, and auto-analyze."""
    from app.ingestion.parser import SUPPORTED_EXTENSIONS
    import uuid

    settings = get_settings()

    # Validate extension
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type: {ext}. Supported: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    # Save file
    upload_dir = os.path.join(settings.ONEDRIVE_SYNC_PATH, client_name, "Uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    # Trigger ingestion + analysis as background tasks
    upload_id = str(uuid.uuid4())
    background_tasks.add_task(_ingest_and_analyze, file_path, client_name, upload_id)

    rel_path = os.path.relpath(file_path, settings.ONEDRIVE_SYNC_PATH).replace("\\", "/")
    return {
        "upload_id": upload_id,
        "file_path": rel_path,
        "file_name": file.filename,
        "status": "processing",
    }


async def _ingest_and_analyze(file_path: str, client_name: str, upload_id: str):
    """Background task: ingest file then run LLM analysis."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Step 1: Ingest (parse, chunk, embed, index)
        from app.dependencies import get_client_doc_index_repo, get_search_service, get_embedding_service
        from app.ingestion.pipeline import run_ingestion
        from app.models.source import IngestJob

        doc_index_repo = await get_client_doc_index_repo(client_name)
        search_service = get_search_service()
        embedding_service = get_embedding_service()

        job = IngestJob(id=upload_id, path=file_path, client_name=client_name)
        await run_ingestion(
            job=job,
            doc_index_repo=doc_index_repo,
            search_service=search_service,
            embedding_service=embedding_service,
        )

        # Step 2: Analyze with LLM
        from app.ingestion.parser import parse_document
        from app.dependencies import get_client_analysis_repo, get_client_memory_repo

        parsed = parse_document(file_path)

        from app.services.analysis import AnalysisService, merge_analysis_into_memory
        analysis_service = AnalysisService()
        await analysis_service.initialize()

        result = await analysis_service.analyze_document(parsed, client_name)
        await analysis_service.close()

        # Store analysis result
        analysis_repo = await get_client_analysis_repo(client_name)
        await analysis_repo.upsert(result.model_dump(mode="json"))

        # Auto-merge into client memory
        memory_repo = await get_client_memory_repo(client_name)
        await merge_analysis_into_memory(result, memory_repo)

        logger.info(
            "Upload analyzed: %s — %d stakeholders, %d actions, %d risks",
            file_path,
            len(result.extracted_stakeholders),
            len(result.extracted_actions),
            len(result.extracted_risks),
        )

    except Exception as e:
        logger.error("Ingest+analyze failed for %s: %s", file_path, e)


def _build_tree(dir_path: str, base_path: str) -> dict:
    name = os.path.basename(dir_path) or "root"
    rel_path = os.path.relpath(dir_path, base_path)
    if rel_path == ".":
        rel_path = ""

    node = {
        "name": name,
        "type": "folder",
        "path": rel_path.replace("\\", "/"),
        "children": [],
    }

    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return node

    for entry in entries:
        if entry.startswith("."):
            continue
        full = os.path.join(dir_path, entry)
        if os.path.isdir(full):
            node["children"].append(_build_tree(full, base_path))
        elif os.path.isfile(full):
            node["children"].append({
                "name": entry,
                "type": "file",
                "path": os.path.relpath(full, base_path).replace("\\", "/"),
                "size": os.path.getsize(full),
                "lastModified": os.path.getmtime(full),
            })

    return node
