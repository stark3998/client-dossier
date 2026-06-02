import asyncio
import uuid

from app.dependencies import get_client_doc_index_repo, get_embedding_service, get_job_repo, get_search_service
from app.models.source import IngestJob


async def get_ingest_status(arguments: dict) -> dict:
    """Return the current status of a background ingestion job."""
    job_id = arguments.get("job_id", "")
    if not job_id:
        return {"error": "job_id is required"}

    job_repo = get_job_repo()
    if job_repo is None:
        return {"error": "Job repository not available"}

    try:
        results = await job_repo.query(
            "SELECT * FROM c WHERE c.id = @id",
            [{"name": "@id", "value": job_id}],
        )
        if not results:
            return {"error": f"No job found with id '{job_id}'"}
        job = results[0]
        return {
            "job_id": job.get("id"),
            "status": job.get("status", "unknown"),
            "client_name": job.get("client_name"),
            "mode": job.get("mode"),
            "files_processed": job.get("files_processed", 0),
            "files_total": job.get("files_total", 0),
            "error": job.get("error"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
        }
    except Exception as exc:
        return {"error": str(exc)}


async def ingest_documents(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    mode = arguments.get("mode", "incremental")
    dry_run = bool(arguments.get("dry_run", False))

    if not client_name:
        raise ValueError("client_name is required")
    if mode not in ("incremental", "complete"):
        raise ValueError("mode must be 'incremental' or 'complete'")

    if dry_run:
        import os
        from app.config import get_settings
        settings = get_settings()
        base = settings.ONEDRIVE_SYNC_PATH
        client_folder = os.path.join(base, client_name)
        file_count = 0
        if os.path.isdir(client_folder):
            for root, _, files in os.walk(client_folder):
                file_count += len(files)
        return {
            "status": "dry_run",
            "client_name": client_name,
            "mode": mode,
            "files_found": file_count,
            "message": "No changes written (dry_run=true)",
        }

    job = IngestJob(
        id=str(uuid.uuid4()),
        path="",
        client_name=client_name,
        mode=mode,
    )

    doc_index_repo = await get_client_doc_index_repo(client_name)
    search_service = get_search_service()
    embedding_service = get_embedding_service()
    job_repo = get_job_repo()

    from app.ingestion.pipeline import run_ingestion

    asyncio.create_task(
        run_ingestion(
            job=job,
            doc_index_repo=doc_index_repo,
            search_service=search_service,
            embedding_service=embedding_service,
            job_repo=job_repo,
            force=(mode == "complete"),
        )
    )

    return {
        "job_id": job.id,
        "status": job.status,
        "mode": job.mode,
        "client_name": client_name,
        "message": "Ingestion started in background",
    }
