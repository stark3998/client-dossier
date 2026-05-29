# backend/app/api/ingest.py
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.models.source import IngestJob

router = APIRouter(prefix="/api/ingest", tags=["ingestion"])

_jobs: dict[str, IngestJob] = {}


class IngestRequest(BaseModel):
    path: Optional[str] = None
    client_name: Optional[str] = None


@router.post("")
async def trigger_ingestion(request: IngestRequest, background_tasks: BackgroundTasks):
    if not request.client_name:
        raise HTTPException(status_code=400, detail="client_name is required")

    job = IngestJob(
        id=str(uuid.uuid4()),
        path=request.path or "",
        client_name=request.client_name,
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
        )
    except Exception as e:
        job.status = "error"
        job.error = str(e)

    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "progress": job.progress,
        "current_file": job.current_file,
        "total_files": job.total_files,
        "processed_files": job.processed_files,
        "error": job.error,
    }
