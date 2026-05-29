from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["briefing"])


@router.get("/api/clients/{client_name}/briefing")
async def get_briefing(client_name: str, since: str = ""):
    from app.dependencies import get_cosmos_manager, get_event_bus
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Services not available")

    client_id = client_name.lower().replace(" ", "-")
    result = {
        "client_name": client_name,
        "since": since,
        "new_analyses": [],
        "overdue_items": [],
        "risk_changes": [],
        "engagement_updates": [],
        "alert_count": 0,
    }

    # Recent analyses
    try:
        repo = await manager.get_client_repo(client_id, "analyses")
        analyses = await repo.query("SELECT * FROM c", [])
        if since:
            analyses = [a for a in analyses if a.get("analyzed_at", "") >= since]
        result["new_analyses"] = [
            {"file_path": a.get("file_path", ""), "doc_type": a.get("doc_type", ""), "summary": a.get("analysis_summary", "")[:200]}
            for a in analyses[:10]
        ]
    except Exception:
        pass

    # Overdue action items
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        repo = await manager.get_client_repo(client_id, "action_items")
        items = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
        overdue = [a for a in items if a.get("due_date") and a["due_date"] < today]
        result["overdue_items"] = [
            {"description": a.get("description", ""), "owner": a.get("owner", ""), "due_date": a.get("due_date", "")}
            for a in overdue
        ]
    except Exception:
        pass

    # Risk changes (recent events)
    event_bus = get_event_bus()
    if event_bus and since:
        events = await event_bus.get_recent(client_name, ["risk_created", "risk_escalated", "risk_updated"], since=since)
        result["risk_changes"] = [
            {"description": e.get("summary", ""), "severity": e.get("severity", ""), "status": "new"}
            for e in events[:10]
        ]

    # Engagement updates
    if event_bus and since:
        events = await event_bus.get_recent(client_name, ["engagement_phase_changed", "status_update_created"], since=since)
        result["engagement_updates"] = [
            {"name": e.get("summary", ""), "phase": "", "change": e.get("event_type", "")}
            for e in events[:10]
        ]

    result["alert_count"] = len(result["overdue_items"]) + len(result["risk_changes"])

    # Health snapshot
    try:
        from app.services.health_scorer import HealthScorer
        scorer = HealthScorer(manager)
        health = await scorer.compute_health(client_name)
        result["health_snapshot"] = health.model_dump(mode="json")
    except Exception:
        pass

    return result
