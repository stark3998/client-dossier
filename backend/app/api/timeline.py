# backend/app/api/timeline.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/clients/{client_name}/timeline", tags=["timeline"])


@router.get("")
async def get_timeline(client_name: str, limit: int = 50):
    """Unified chronological timeline of all client events."""
    from app.dependencies import get_cosmos_manager
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Services not available")

    client_id = client_name.lower().replace(" ", "-")
    events: list[dict] = []

    # Interactions
    try:
        repo = await manager.get_client_repo(client_id, "interactions")
        items = await repo.query("SELECT * FROM c", [])
        for item in items:
            events.append({
                "type": "interaction",
                "subtype": item.get("type", "meeting"),
                "date": item.get("date", ""),
                "summary": item.get("summary", ""),
                "participants": item.get("participants", []),
                "id": item.get("id"),
                "source": "interactions",
            })
    except Exception:
        pass

    # Status updates
    try:
        repo = await manager.get_client_repo(client_id, "status_updates")
        items = await repo.query("SELECT * FROM c", [])
        for item in items:
            events.append({
                "type": "status_update",
                "subtype": item.get("sentiment", "neutral"),
                "date": item.get("date", ""),
                "summary": item.get("summary", ""),
                "author": item.get("author", ""),
                "id": item.get("id"),
                "source": "status_updates",
            })
    except Exception:
        pass

    # Analysis events
    try:
        repo = await manager.get_client_repo(client_id, "analyses")
        items = await repo.query("SELECT * FROM c", [])
        for item in items:
            events.append({
                "type": "analysis",
                "subtype": item.get("doc_type", "unknown"),
                "date": item.get("analyzed_at", ""),
                "summary": item.get("analysis_summary", ""),
                "file_path": item.get("file_path", ""),
                "id": item.get("id"),
                "source": "analyses",
            })
    except Exception:
        pass

    # Sort by date descending
    events.sort(key=lambda e: e.get("date", ""), reverse=True)

    return {"events": events[:limit], "total": len(events)}
