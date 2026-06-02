from datetime import datetime, timezone

from app.dependencies import get_cosmos_manager, get_event_bus


async def generate_briefing(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    since = arguments.get("since", "")

    if not client_name:
        raise ValueError("client_name is required")

    manager = get_cosmos_manager()
    if manager is None:
        raise RuntimeError("Cosmos service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    result: dict = {
        "client_name": client_name,
        "since": since,
        "new_analyses": [],
        "overdue_items": [],
        "risk_changes": [],
        "engagement_updates": [],
        "alert_count": 0,
    }

    try:
        repo = await manager.get_client_repo(client_id, "analyses")
        analyses = await repo.query("SELECT * FROM c", [])
        if since:
            analyses = [a for a in analyses if a.get("analyzed_at", "") >= since]
        result["new_analyses"] = [
            {
                "file_path": a.get("file_path", ""),
                "doc_type": a.get("doc_type", ""),
                "summary": a.get("analysis_summary", "")[:200],
            }
            for a in analyses[:10]
        ]
    except Exception:
        pass

    try:
        today = datetime.now(timezone.utc).date().isoformat()
        repo = await manager.get_client_repo(client_id, "action_items")
        items = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
        overdue = [a for a in items if a.get("due_date") and a["due_date"] < today]
        result["overdue_items"] = [
            {
                "description": a.get("description", ""),
                "owner": a.get("owner", ""),
                "due_date": a.get("due_date", ""),
            }
            for a in overdue
        ]
    except Exception:
        pass

    event_bus = get_event_bus()
    if event_bus and since:
        try:
            events = await event_bus.get_recent(
                client_name,
                ["risk_created", "risk_escalated", "risk_updated"],
                since=since,
            )
            result["risk_changes"] = [
                {"description": e.get("summary", ""), "severity": e.get("severity", "")}
                for e in events[:10]
            ]
            events = await event_bus.get_recent(
                client_name,
                ["engagement_phase_changed", "status_update_created"],
                since=since,
            )
            result["engagement_updates"] = [
                {"name": e.get("summary", ""), "change": e.get("event_type", "")}
                for e in events[:10]
            ]
        except Exception:
            pass

    result["alert_count"] = len(result["overdue_items"]) + len(result["risk_changes"])

    try:
        from app.services.health_scorer import HealthScorer
        scorer = HealthScorer(manager)
        health = await scorer.compute_health(client_name)
        result["health_snapshot"] = health.model_dump(mode="json")
    except Exception:
        pass

    return result
