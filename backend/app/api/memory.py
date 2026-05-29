# backend/app/api/memory.py
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/{client_name}")
async def get_memory(client_name: str):
    try:
        from app.dependencies import get_client_memory_repo
        repo = await get_client_memory_repo(client_name)
    except Exception:
        raise HTTPException(status_code=503, detail="Services not available")

    if repo is None:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    memory = await repo.get(client_id, client_id)
    if memory is None:
        return {"client_name": client_name, "id": client_id}
    return memory


@router.put("/{client_name}")
async def update_memory(client_name: str, body: dict):
    try:
        from app.dependencies import get_client_memory_repo
        repo = await get_client_memory_repo(client_name)
    except Exception:
        raise HTTPException(status_code=503, detail="Services not available")

    if repo is None:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    existing = await repo.get(client_id, client_id) or {"id": client_id, "client_name": client_name}
    existing.update(body)
    existing["id"] = client_id
    existing["last_updated"] = datetime.now(timezone.utc).isoformat()
    await repo.upsert(existing)
    return existing
