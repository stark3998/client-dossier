# backend/app/agent/communication_plugin.py
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class CommunicationPlugin:
    def __init__(self, cosmos_manager, access=None):
        self._manager = cosmos_manager
        self._access = access  # CommunicationAccess instance

    def _client_id(self, client_name: str) -> str:
        return client_name.lower().replace(" ", "-")

    @kernel_function(
        name="recall_client_emails",
        description="Retrieve recent emails attributed to a client. Returns sender, subject, date, and preview."
    )
    async def recall_client_emails(self, client_name: str, days: int = 7) -> str:
        client_id = self._client_id(client_name)
        try:
            repo = await self._manager.get_client_repo(client_id, "emails")
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            items = await repo.query(
                "SELECT c.id, c.subject, c.sender, c.recipients, c.body_preview, "
                "c.received_at, c.folder, c.attribution_reason, c.has_draft_reply "
                "FROM c WHERE c.received_at >= @since ORDER BY c.received_at DESC",
                [{"name": "@since", "value": since}],
            )
            return json.dumps(items[:50], indent=2, default=str)
        except Exception as e:
            logger.warning("recall_client_emails error: %s", e)
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="recall_client_meetings",
        description="Retrieve meeting logs for a client including attendees, agenda, and transcript summaries."
    )
    async def recall_client_meetings(self, client_name: str, days: int = 30) -> str:
        client_id = self._client_id(client_name)
        try:
            repo = await self._manager.get_client_repo(client_id, "meetings")
            since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            items = await repo.query(
                "SELECT c.id, c.subject, c.organizer, c.attendees, c.start_time, "
                "c.end_time, c.my_response, c.is_teams_meeting, c.transcript_summary, "
                "c.action_items_extracted "
                "FROM c WHERE c.start_time >= @since ORDER BY c.start_time DESC",
                [{"name": "@since", "value": since}],
            )
            return json.dumps(items[:30], indent=2, default=str)
        except Exception as e:
            logger.warning("recall_client_meetings error: %s", e)
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="create_draft_reply",
        description="Generate a draft reply to a specific client email and save it for review. Provide the email_id and optional context to include in the reply."
    )
    async def create_draft_reply(self, client_name: str, email_id: str, context: str = "") -> str:
        client_id = self._client_id(client_name)
        try:
            email_repo = await self._manager.get_client_repo(client_id, "emails")
            draft_repo = await self._manager.get_client_repo(client_id, "draft_replies")

            email = await email_repo.get(email_id, client_name)
            if not email:
                return json.dumps({"error": f"Email {email_id} not found"})

            # Check for existing draft
            existing = await draft_repo.query(
                "SELECT * FROM c WHERE c.email_id = @eid",
                [{"name": "@eid", "value": email_id}],
            )
            if existing:
                return json.dumps({"status": "already_exists", "draft_id": existing[0]["id"]})

            from app.models.communication import DraftReply
            body_hint = f"\n\nContext to include: {context}" if context else ""
            draft = DraftReply(
                client_name=client_name,
                email_id=email_id,
                subject=f"Re: {email.get('subject', '')}",
                to=[email.get("sender", "")],
                body=f"[Draft reply for: {email.get('subject', '')}]{body_hint}\n\nPlease edit this draft before sending.",
            )
            await draft_repo.upsert(draft.model_dump(mode="json"))
            return json.dumps({"status": "created", "draft_id": draft.id})
        except Exception as e:
            logger.warning("create_draft_reply error: %s", e)
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="list_pending_drafts",
        description="List draft replies awaiting review for a client."
    )
    async def list_pending_drafts(self, client_name: str) -> str:
        client_id = self._client_id(client_name)
        try:
            repo = await self._manager.get_client_repo(client_id, "draft_replies")
            items = await repo.query(
                "SELECT c.id, c.subject, c.to, c.status, c.created_at FROM c "
                "WHERE c.status = 'pending_review' OR c.status = 'edited' "
                "ORDER BY c.created_at DESC",
                [],
            )
            return json.dumps(items[:20], indent=2, default=str)
        except Exception as e:
            logger.warning("list_pending_drafts error: %s", e)
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="get_meeting_transcript",
        description="Get the transcript summary for a specific Teams meeting by meeting_id."
    )
    async def get_meeting_transcript(self, client_name: str, meeting_id: str) -> str:
        client_id = self._client_id(client_name)
        try:
            repo = await self._manager.get_client_repo(client_id, "meetings")
            meeting = await repo.get(meeting_id, client_name)
            if not meeting:
                return json.dumps({"error": f"Meeting {meeting_id} not found"})
            summary = meeting.get("transcript_summary")
            if not summary:
                # Try to fetch live if we have the online meeting ID
                oid = meeting.get("online_meeting_id")
                if oid and self._access:
                    summary = await self._access.get_meeting_transcript(oid)
                    if summary:
                        meeting["transcript_summary"] = summary
                        await repo.upsert(meeting)
            return json.dumps({
                "meeting_id": meeting_id,
                "subject": meeting.get("subject"),
                "transcript_summary": summary or "No transcript available.",
                "action_items": meeting.get("action_items_extracted", []),
            }, default=str)
        except Exception as e:
            logger.warning("get_meeting_transcript error: %s", e)
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="get_communication_summary",
        description="Get a high-level communication summary for a client: recent email count, upcoming meetings, pending drafts."
    )
    async def get_communication_summary(self, client_name: str) -> str:
        client_id = self._client_id(client_name)
        summary: dict = {}
        try:
            email_repo = await self._manager.get_client_repo(client_id, "emails")
            since_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            emails = await email_repo.query(
                "SELECT VALUE COUNT(1) FROM c WHERE c.received_at >= @since",
                [{"name": "@since", "value": since_7d}],
            )
            summary["emails_last_7d"] = emails[0] if emails else 0
        except Exception:
            summary["emails_last_7d"] = 0

        try:
            meeting_repo = await self._manager.get_client_repo(client_id, "meetings")
            now = datetime.now(timezone.utc).isoformat()
            upcoming = await meeting_repo.query(
                "SELECT VALUE COUNT(1) FROM c WHERE c.start_time >= @now",
                [{"name": "@now", "value": now}],
            )
            summary["upcoming_meetings"] = upcoming[0] if upcoming else 0
        except Exception:
            summary["upcoming_meetings"] = 0

        try:
            draft_repo = await self._manager.get_client_repo(client_id, "draft_replies")
            drafts = await draft_repo.query(
                "SELECT VALUE COUNT(1) FROM c WHERE c.status = 'pending_review'",
                [],
            )
            summary["pending_drafts"] = drafts[0] if drafts else 0
        except Exception:
            summary["pending_drafts"] = 0

        return json.dumps(summary, default=str)
