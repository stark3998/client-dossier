from app.dependencies import get_cosmos_manager


def _client_id(client_name: str) -> str:
    return client_name.lower().replace(" ", "-")


async def get_client_timeline(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    limit = min(int(arguments.get("limit", 20)), 200)
    event_types = arguments.get("event_types")

    if not client_name:
        raise ValueError("client_name is required")

    manager = get_cosmos_manager()
    if manager is None:
        raise RuntimeError("Cosmos service not initialized")

    cid = _client_id(client_name)
    events: list[dict] = []

    if not event_types or "interaction" in event_types:
        try:
            repo = await manager.get_client_repo(cid, "interactions")
            items = await repo.query("SELECT * FROM c", [])
            for item in items:
                events.append({
                    "type": "interaction",
                    "subtype": item.get("type", "meeting"),
                    "date": item.get("date", ""),
                    "summary": item.get("summary", ""),
                    "participants": item.get("participants", []),
                    "id": item.get("id"),
                })
        except Exception:
            pass

    if not event_types or "status_update" in event_types:
        try:
            repo = await manager.get_client_repo(cid, "status_updates")
            items = await repo.query("SELECT * FROM c", [])
            for item in items:
                events.append({
                    "type": "status_update",
                    "subtype": item.get("sentiment", "neutral"),
                    "date": item.get("date", ""),
                    "summary": item.get("summary", ""),
                    "author": item.get("author", ""),
                    "id": item.get("id"),
                })
        except Exception:
            pass

    if not event_types or "analysis" in event_types:
        try:
            repo = await manager.get_client_repo(cid, "analyses")
            items = await repo.query("SELECT * FROM c", [])
            for item in items:
                events.append({
                    "type": "analysis",
                    "subtype": item.get("doc_type", "unknown"),
                    "date": item.get("analyzed_at", ""),
                    "summary": item.get("analysis_summary", "")[:200],
                    "file_path": item.get("file_path", ""),
                    "id": item.get("id"),
                })
        except Exception:
            pass

    events.sort(key=lambda e: e.get("date", ""), reverse=True)
    return {"client_name": client_name, "events": events[:limit], "total": len(events)}
