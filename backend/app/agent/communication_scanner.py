# backend/app/agent/communication_scanner.py
"""
Background scanner that periodically reads emails and calendar items from Outlook/Graph,
attributes them to clients via per-client CommunicationConfig, generates draft replies,
fetches Teams transcripts, and updates agent memory.
Mirrors the AlertChecker pattern.
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.communication import (
    CommunicationConfig,
    DraftReply,
    MeetingLog,
    RawCalendarItem,
    RawEmail,
    ScannedEmail,
)
from app.services.communication_access import CommunicationAccess

logger = logging.getLogger(__name__)


class CommunicationScanner:
    def __init__(self, cosmos_manager, access: CommunicationAccess, kernel=None, event_bus=None):
        self._manager = cosmos_manager
        self._access = access
        self._kernel = kernel
        self._event_bus = event_bus
        self._task: Optional[asyncio.Task] = None

    async def start(self, interval_seconds: int = 900):
        self._task = asyncio.create_task(self._run_loop(interval_seconds))

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _run_loop(self, interval: int):
        while True:
            try:
                await asyncio.sleep(interval)
                await self._scan_all_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Communication scanner error: %s", e)

    async def _scan_all_clients(self):
        try:
            master = self._manager.get_master_repo()
            clients = await master.query("SELECT * FROM c", [])
            for client in clients:
                name = client.get("name") or client.get("client_name") or client.get("id", "")
                if not name:
                    continue
                config = await self._get_config(name)
                if config:
                    await self.scan_client(name, config)
        except Exception as e:
            logger.warning("Failed to scan all clients: %s", e)

    async def _get_config(self, client_name: str) -> Optional[CommunicationConfig]:
        client_id = client_name.lower().replace(" ", "-")
        try:
            repo = await self._manager.get_client_repo(client_id, "communication_config")
            raw = await repo.get(client_id, client_id)
            if raw:
                return CommunicationConfig(**raw)
        except Exception:
            pass
        return None

    async def scan_client(self, client_name: str, config: CommunicationConfig):
        """Full scan cycle for one client — emails, calendar, transcripts, memory."""
        client_id = client_name.lower().replace(" ", "-")
        since = datetime.now(timezone.utc) - timedelta(days=config.scan_interval_minutes * 2 / 1440 + 7)

        await self._scan_emails(client_name, client_id, config, since)
        await self._scan_calendar(client_name, client_id, config, since)

    async def _scan_emails(
        self,
        client_name: str,
        client_id: str,
        config: CommunicationConfig,
        since: datetime,
    ):
        email_repo = await self._manager.get_client_repo(client_id, "emails")
        draft_repo = await self._manager.get_client_repo(client_id, "draft_replies")

        for account in config.accounts:
            folders = account.folders or ["Inbox"]
            if config.scan_sent and "Sent Items" not in folders:
                folders = list(folders) + ["Sent Items"]

            for folder in folders:
                try:
                    raw_emails = await self._access.get_emails(
                        account.display_name, folder, since
                    )
                    for raw in raw_emails:
                        reason = self._attribute(raw, config)
                        if reason is None:
                            continue

                        email_id = hashlib.sha256(raw.message_id.encode()).hexdigest()[:36] if raw.message_id else None
                        if not email_id:
                            continue

                        existing = await email_repo.get(email_id, client_name)
                        if existing:
                            continue

                        scanned = ScannedEmail(
                            id=email_id,
                            client_name=client_name,
                            message_id=raw.message_id,
                            subject=raw.subject,
                            sender=raw.sender,
                            recipients=raw.recipients,
                            body_preview=raw.body[:500],
                            body_full=raw.body,
                            received_at=raw.received_at,
                            folder=raw.folder,
                            account=raw.account,
                            thread_id=raw.thread_id,
                            has_attachment=raw.has_attachment,
                            attachment_names=raw.attachment_names,
                            attribution_reason=reason,
                        )
                        await email_repo.upsert(scanned.model_dump(mode="json"))

                        # Auto-draft: create a reply for inbound emails from client contacts if enabled
                        if config.auto_draft and folder.lower() in ("inbox", "inbox"):
                            await self._maybe_create_draft(
                                client_name, client_id, scanned, draft_repo, config
                            )

                        await self._publish_event(client_name, "new_email", email_id, f"New email: {raw.subject[:60]}")
                except Exception as e:
                    logger.warning("Email scan error for %s/%s/%s: %s", client_name, account.display_name, folder, e)

    async def _scan_calendar(
        self,
        client_name: str,
        client_id: str,
        config: CommunicationConfig,
        since: datetime,
    ):
        meeting_repo = await self._manager.get_client_repo(client_id, "meetings")
        until = datetime.now(timezone.utc) + timedelta(days=30)

        for account in config.accounts:
            try:
                raw_items = await self._access.get_calendar_events(
                    account.display_name, since, until
                )
                for raw in raw_items:
                    if not self._meeting_matches(raw, config):
                        continue

                    meeting_id = hashlib.sha256(raw.global_id.encode()).hexdigest()[:36] if raw.global_id else None
                    if not meeting_id:
                        continue

                    existing = await meeting_repo.get(meeting_id, client_name)
                    if existing:
                        # Check if we should fetch a transcript that wasn't available before
                        if raw.is_teams_meeting and raw.online_meeting_id and not existing.get("transcript_summary"):
                            summary = await self._fetch_transcript_summary(raw.online_meeting_id, client_name)
                            if summary:
                                existing["transcript_summary"] = summary
                                existing["action_items_extracted"] = await self._extract_action_items(summary)
                                await meeting_repo.upsert(existing)
                        continue

                    transcript_summary: Optional[str] = None
                    action_items: list[str] = []
                    if raw.is_teams_meeting and raw.online_meeting_id and raw.start_time < datetime.now(timezone.utc):
                        transcript_summary = await self._fetch_transcript_summary(raw.online_meeting_id, client_name)
                        if transcript_summary:
                            action_items = await self._extract_action_items(transcript_summary)

                    meeting = MeetingLog(
                        id=meeting_id,
                        client_name=client_name,
                        subject=raw.subject,
                        organizer=raw.organizer,
                        attendees=raw.attendees,
                        start_time=raw.start_time,
                        end_time=raw.end_time,
                        location=raw.location,
                        agenda=raw.body,
                        is_teams_meeting=raw.is_teams_meeting,
                        teams_join_url=raw.teams_join_url,
                        online_meeting_id=raw.online_meeting_id,
                        my_response=raw.my_response,
                        transcript_summary=transcript_summary,
                        action_items_extracted=action_items,
                    )
                    await meeting_repo.upsert(meeting.model_dump(mode="json"))

                    await self._publish_event(
                        client_name, "new_meeting", meeting_id,
                        f"Meeting logged: {raw.subject[:60]}"
                    )

                    # Update client memory with meeting info
                    await self._update_memory_from_meeting(client_name, client_id, meeting)
            except Exception as e:
                logger.warning("Calendar scan error for %s/%s: %s", client_name, account.display_name, e)

    def _attribute(self, raw: RawEmail, config: CommunicationConfig) -> Optional[str]:
        """Return attribution reason if this email belongs to the client, else None."""
        all_addresses = [raw.sender] + raw.recipients
        lower_addresses = [a.lower() for a in all_addresses if a]

        for domain in config.domains:
            d = domain.lower().lstrip("@")
            if any(f"@{d}" in a for a in lower_addresses):
                return "domain_match"

        for contact in config.contacts:
            if contact.lower() in lower_addresses:
                return "contact_match"

        text = f"{raw.subject} {raw.body}".lower()
        for kw in config.keywords:
            if kw.lower() in text:
                return "keyword_match"

        return None

    def _meeting_matches(self, raw: RawCalendarItem, config: CommunicationConfig) -> bool:
        attendee_emails = [a.email.lower() for a in raw.attendees if a.email]

        for domain in config.domains:
            d = domain.lower().lstrip("@")
            if any(f"@{d}" in e for e in attendee_emails):
                return True

        for contact in config.contacts:
            if contact.lower() in attendee_emails:
                return True

        text = f"{raw.subject} {raw.body}".lower()
        for kw in config.keywords:
            if kw.lower() in text:
                return True

        return False

    async def _maybe_create_draft(
        self,
        client_name: str,
        client_id: str,
        email: ScannedEmail,
        draft_repo,
        config: CommunicationConfig,
    ):
        # Only draft for emails from client stakeholders (senders matching domain/contact)
        sender_lower = email.sender.lower()
        is_client_sender = any(
            domain.lower().lstrip("@") in sender_lower for domain in config.domains
        ) or any(c.lower() == sender_lower for c in config.contacts)

        if not is_client_sender:
            return

        # Don't create duplicate drafts for the same email
        existing = await draft_repo.query(
            "SELECT * FROM c WHERE c.email_id = @eid",
            [{"name": "@eid", "value": email.id}],
        )
        if existing:
            return

        body = await self._generate_draft_body(client_name, email)
        draft = DraftReply(
            client_name=client_name,
            email_id=email.id,
            subject=f"Re: {email.subject}",
            to=[email.sender],
            body=body,
        )
        await draft_repo.upsert(draft.model_dump(mode="json"))

    async def _generate_draft_body(self, client_name: str, email: ScannedEmail) -> str:
        if self._kernel is None:
            return f"[Auto-draft] Thank you for your email regarding: {email.subject}\n\nPlease review and edit this draft before sending."

        try:
            from semantic_kernel.contents import ChatHistory
            chat = ChatHistory()
            chat.add_system_message(
                f"You are a professional consultant. Draft a concise, professional email reply "
                f"for the client '{client_name}'. Keep it brief (3-5 sentences). "
                f"Do not include subject line. Start with a greeting."
            )
            chat.add_user_message(
                f"Original email from {email.sender}:\nSubject: {email.subject}\n\n{email.body_preview}"
            )
            from app.agent.kernel import get_execution_settings
            settings = get_execution_settings()
            result = await self._kernel.invoke_prompt(
                prompt="{{$chat_history}}",
                chat_history=chat,
                settings=settings,
            )
            return str(result)
        except Exception as e:
            logger.warning("Draft generation failed: %s", e)
            return f"Thank you for your email. We will review and respond shortly.\n\n[Auto-generated draft for: {email.subject}]"

    async def _fetch_transcript_summary(self, online_meeting_id: str, client_name: str) -> Optional[str]:
        try:
            transcript = await self._access.get_meeting_transcript(online_meeting_id)
            if not transcript:
                return None
            return await self._summarize_transcript(transcript, client_name)
        except Exception as e:
            logger.warning("Transcript fetch failed for %s: %s", online_meeting_id, e)
            return None

    async def _summarize_transcript(self, transcript: str, client_name: str) -> str:
        if self._kernel is None:
            return transcript[:1000]
        try:
            from semantic_kernel.contents import ChatHistory
            chat = ChatHistory()
            chat.add_system_message(
                f"Summarize this Teams meeting transcript for client '{client_name}'. "
                f"Include: key topics discussed, decisions made, and next steps. "
                f"Keep it under 300 words."
            )
            chat.add_user_message(transcript[:8000])
            from app.agent.kernel import get_execution_settings
            result = await self._kernel.invoke_prompt(
                prompt="{{$chat_history}}",
                chat_history=chat,
                settings=get_execution_settings(),
            )
            return str(result)
        except Exception as e:
            logger.warning("Transcript summarization failed: %s", e)
            return transcript[:500]

    async def _extract_action_items(self, summary: str) -> list[str]:
        if self._kernel is None:
            return []
        try:
            from semantic_kernel.contents import ChatHistory
            chat = ChatHistory()
            chat.add_system_message(
                "Extract action items from this meeting summary. "
                "Return each as a short sentence starting with a verb. "
                "Return as JSON array of strings, nothing else."
            )
            chat.add_user_message(summary)
            from app.agent.kernel import get_execution_settings
            result = await self._kernel.invoke_prompt(
                prompt="{{$chat_history}}",
                chat_history=chat,
                settings=get_execution_settings(),
            )
            import json
            text = str(result).strip()
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1:
                return json.loads(text[start:end + 1])
        except Exception:
            pass
        return []

    async def _update_memory_from_meeting(self, client_name: str, client_id: str, meeting: MeetingLog):
        try:
            repo = await self._manager.get_client_repo(client_id, "memories")
            memory = await repo.get(client_id, client_id)
            if memory is None:
                memory = {"id": client_id, "client_name": client_name}

            # Add attendees as known stakeholders if not already present
            existing_stakeholders = memory.get("key_stakeholders", [])
            existing_emails = {s.get("email", "").lower() for s in existing_stakeholders}
            for attendee in meeting.attendees:
                if attendee.email and attendee.email.lower() not in existing_emails:
                    existing_stakeholders.append({"name": attendee.name, "email": attendee.email})
                    existing_emails.add(attendee.email.lower())
            memory["key_stakeholders"] = existing_stakeholders
            memory["last_updated"] = datetime.now(timezone.utc).isoformat()
            await repo.upsert(memory)
        except Exception as e:
            logger.warning("Memory update from meeting failed: %s", e)

    async def _publish_event(self, client_name: str, event_type: str, entity_id: str, summary: str):
        if self._event_bus is None:
            return
        try:
            from app.models.event import ClientEvent
            await self._event_bus.publish(ClientEvent(
                client_name=client_name,
                event_type=f"comm_{event_type}",
                entity_type=event_type,
                entity_id=entity_id,
                summary=summary,
                severity="info",
            ))
        except Exception as e:
            logger.warning("Event publish failed: %s", e)
