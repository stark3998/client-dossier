# backend/app/api/clients.py
import os
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("")
async def list_clients():
    """List all known clients from filesystem and master database."""
    settings = get_settings()
    clients = set()

    # Discover from filesystem
    sync_path = settings.ONEDRIVE_SYNC_PATH
    if os.path.isdir(sync_path):
        for entry in os.listdir(sync_path):
            full = os.path.join(sync_path, entry)
            if os.path.isdir(full) and not entry.startswith("."):
                clients.add(entry)

    # Discover from master database
    try:
        from app.dependencies import get_master_repo
        repo = get_master_repo()
        if repo is not None:
            records = await repo.query("SELECT c.client_name FROM c", [])
            for rec in records:
                name = rec.get("client_name", "")
                if name:
                    clients.add(name)
    except Exception as e:
        logger.warning("Failed to query master repo: %s", e)

    return {"clients": sorted(clients), "count": len(clients)}


@router.post("")
async def onboard_client(body: dict):
    """Create a new client: folder + master record + isolated database."""
    settings = get_settings()
    client_name = body.get("client_name", "").strip()
    if not client_name:
        raise HTTPException(status_code=400, detail="client_name is required")

    client_id = client_name.lower().replace(" ", "-")

    # Create folder
    client_dir = os.path.join(settings.ONEDRIVE_SYNC_PATH, client_name)
    os.makedirs(client_dir, exist_ok=True)

    try:
        from app.dependencies import get_master_repo, get_cosmos_manager
        master = get_master_repo()
        manager = get_cosmos_manager()

        if master is not None:
            # Register in master database
            existing = await master.get(client_id, client_id)
            if not existing:
                await master.upsert({
                    "id": client_id,
                    "client_name": client_name,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "status": "active",
                })

        if manager is not None:
            # Create per-client isolated database
            await manager.ensure_client_database(client_id)

            # Initialize empty memory in client's database
            memory_repo = await manager.get_client_repo(client_id, "memories")
            existing_mem = await memory_repo.get(client_id, client_id)
            if not existing_mem:
                await memory_repo.upsert({
                    "id": client_id,
                    "client_name": client_name,
                    "industry": None,
                    "key_stakeholders": [],
                    "active_engagements": [],
                    "financials_summary": None,
                    "pain_points": [],
                    "strategic_priorities": [],
                    "past_deliverables": [],
                    "open_action_items": [],
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "sources": [],
                })

    except Exception as e:
        logger.warning("Failed to initialize client: %s", e)

    return {"client_name": client_name, "client_id": client_id, "status": "created"}
