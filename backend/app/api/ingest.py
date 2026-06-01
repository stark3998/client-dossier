# backend/app/api/ingest.py
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Literal, Optional

from app.models.source import IngestJob

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

_jobs: dict[str, IngestJob] = {}


class IngestRequest(BaseModel):
    path: Optional[str] = None
    client_name: Optional[str] = None
    mode: Literal["incremental", "complete"] = "incremental"


@router.get("/indexed-files")
async def get_indexed_files(client_name: str):
    if not client_name:
        raise HTTPException(status_code=400, detail="client_name is required")
    from app.dependencies import get_client_doc_index_repo
    repo = await get_client_doc_index_repo(client_name)
    docs = await repo.query("SELECT c.file_path, c.last_indexed FROM c")
    return {"files": docs}


@router.post("")
async def trigger_ingestion(request: IngestRequest, background_tasks: BackgroundTasks):
    if not request.client_name:
        raise HTTPException(status_code=400, detail="client_name is required")

    job = IngestJob(
        id=str(uuid.uuid4()),
        path=request.path or "",
        client_name=request.client_name,
        mode=request.mode,
    )
    _jobs[job.id] = job

    try:
        from app.dependencies import get_client_doc_index_repo, get_search_service, get_embedding_service
        doc_index_repo = await get_client_doc_index_repo(request.client_name)
        search_service = get_search_service()
        embedding_service = get_embedding_service()

        from app.ingestion.pipeline import run_ingestion
        background_tasks.add_task(
            run_ingestion,
            job=job,
            doc_index_repo=doc_index_repo,
            search_service=search_service,
            embedding_service=embedding_service,
            force=(request.mode == "complete"),
        )
    except Exception as e:
        job.status = "error"
        job.error = str(e)

    return {"job_id": job.id, "status": job.status, "mode": job.mode}


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "mode": job.mode,
        "progress": job.progress,
        "current_file": job.current_file,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "skipped_files": job.skipped_files,
        "error": job.error,
    }
