from datetime import datetime, timedelta, timezone

from app.dependencies import get_cosmos_manager


def _client_id(client_name: str) -> str:
    return client_name.lower().replace(" ", "-")


async def get_client_communications(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    comm_type = arguments.get("comm_type", "all")
    limit = min(int(arguments.get("limit", 20)), 100)
    lookback_days = arguments.get("lookback_days")

    if not client_name:
        raise ValueError("client_name is required")

    manager = get_cosmos_manager()
    if manager is None:
        raise RuntimeError("Cosmos service not initialized")

    cid = _client_id(client_name)
    result: dict = {"client_name": client_name}

    if comm_type in ("emails", "all"):
        try:
            days = int(lookback_days) if lookback_days else 7
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            repo = await manager.get_client_repo(cid, "emails")
            emails = await repo.query(
                "SELECT c.id, c.subject, c.sender, c.recipients, c.body_preview, "
                "c.received_at, c.folder, c.has_draft_reply, c.has_attachment "
                "FROM c WHERE c.received_at >= @since ORDER BY c.received_at DESC",
                [{"name": "@since", "value": since}],
            )
            result["emails"] = emails[:limit]
            result["email_count"] = len(emails[:limit])
        except Exception:
            result["emails"] = []

    if comm_type in ("meetings", "all"):
        try:
            days = int(lookback_days) if lookback_days else 30
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            repo = await manager.get_client_repo(cid, "meetings")
            meetings = await repo.query(
                "SELECT c.id, c.subject, c.organizer, c.attendees, c.start_time, c.end_time, "
                "c.is_teams_meeting, c.my_response, c.transcript_summary "
                "FROM c WHERE c.start_time >= @since ORDER BY c.start_time DESC",
                [{"name": "@since", "value": since}],
            )
            result["meetings"] = meetings[:limit]
            result["meeting_count"] = len(meetings[:limit])
        except Exception:
            result["meetings"] = []

    if comm_type in ("drafts", "all"):
        try:
            repo = await manager.get_client_repo(cid, "draft_replies")
            drafts = await repo.query(
                "SELECT * FROM c WHERE c.status != 'discarded' ORDER BY c.created_at DESC",
                [],
            )
            result["drafts"] = drafts[:limit]
            result["draft_count"] = len(drafts[:limit])
        except Exception:
            result["drafts"] = []

    return result
