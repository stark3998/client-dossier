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
from typing import Callable, Optional

from app.models.communication import (
    CommunicationConfig,
    DraftReply,
    EmailClassification,
    MeetingClassification,
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
        logger.info("_get_config: looking up config for client=%r  client_id=%r", client_name, client_id)
        try:
            repo = await self._manager.get_client_repo(client_id, "communication_config")
            raw = await repo.get(client_id, client_id)
            if raw:
                cfg = CommunicationConfig(**raw)
                logger.info(
                    "_get_config: loaded config for %r  domains=%s  keywords=%s  "
                    "contacts=%s  accounts=%s  scan_sent=%s",
                    client_name, cfg.domains, cfg.keywords,
                    cfg.contacts,
                    [a.display_name for a in cfg.accounts],
                    cfg.scan_sent,
                )
                return cfg
            else:
                logger.warning(
                    "_get_config: no config document found for client_id=%r  "
                    "(checked partition+id = %r). "
                    "Go to Communications > Config tab and save settings first.",
                    client_id, client_id,
                )
        except Exception as e:
            logger.error("_get_config: exception loading config for %r: %s", client_name, e, exc_info=True)
        return None

    async def scan_client(
        self,
        client_name: str,
        config: CommunicationConfig,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ):
        """Full scan cycle for one client — emails, calendar, transcripts, memory."""
        client_id = client_name.lower().replace(" ", "-")
        if config.lookback_days == 0:
            since = datetime(2000, 1, 1, tzinfo=timezone.utc)  # all time
        else:
            since = datetime.now(timezone.utc) - timedelta(days=config.lookback_days)
        logger.info(
            "scan_client START  client=%r  since=%s  accounts=%s  "
            "domains=%s  keywords=%s  contacts=%s",
            client_name, since.isoformat(),
            [a.display_name for a in config.accounts],
            config.domains, config.keywords, config.contacts,
        )

        if progress_cb:
            progress_cb({"phase": "emails", "message": f"Scanning emails since {since.strftime('%Y-%m-%d')}"})

        await self._scan_emails(client_name, client_id, config, since, progress_cb=progress_cb)

        if progress_cb:
            progress_cb({"phase": "calendar", "message": "Scanning calendar events"})

        await self._scan_calendar(client_name, client_id, config, since)
        logger.info("scan_client DONE  client=%r", client_name)

        if progress_cb:
            progress_cb({"phase": "done", "message": "Scan complete"})

    async def _scan_emails(
        self,
        client_name: str,
        client_id: str,
        config: CommunicationConfig,
        since: datetime,
        progress_cb: Optional[Callable[[dict], None]] = None,
    ):
        email_repo = await self._manager.get_client_repo(client_id, "emails")
        draft_repo = await self._manager.get_client_repo(client_id, "draft_replies")

        total_fetched = 0
        total_attributed = 0
        total_new = 0

        for account in config.accounts:
            folders = account.folders or ["Inbox"]
            if config.scan_sent and "Sent Items" not in folders:
                folders = list(folders) + ["Sent Items"]

            logger.info(
                "_scan_emails: account=%r  scanning folders=%s",
                account.display_name, folders,
            )

            if progress_cb:
                progress_cb({
                    "current_account": account.display_name,
                    "current_folder": None,
                    "message": f"Account: {account.display_name}",
                })

            for folder in folders:
                if progress_cb:
                    progress_cb({
                        "current_account": account.display_name,
                        "current_folder": folder,
                        "folder_status": "fetching",
                        "message": f"Fetching {account.display_name} / {folder}…",
                    })
                try:
                    raw_emails = await self._access.get_emails(
                        account.display_name, folder, since
                    )
                    total_fetched += len(raw_emails)
                    logger.info(
                        "_scan_emails: fetched %d emails from %r/%r",
                        len(raw_emails), account.display_name, folder,
                    )

                    if progress_cb:
                        progress_cb({
                            "current_account": account.display_name,
                            "current_folder": folder,
                            "folder_status": "attributing",
                            "folder_fetched": len(raw_emails),
                            "message": f"Attributing {len(raw_emails)} emails in {folder}…",
                            "totals_fetched": total_fetched,
                        })

                    attributed_in_folder = 0
                    skipped_attribution = 0
                    for raw in raw_emails:
                        cls = self._attribute(raw, config)
                        if cls is None:
                            skipped_attribution += 1
                            logger.debug(
                                "_scan_emails: SKIP (no attribution)  subject=%r  sender=%r",
                                raw.subject, raw.sender,
                            )
                            continue

                        attributed_in_folder += 1
                        total_attributed += 1
                        logger.debug(
                            "_scan_emails: ATTRIBUTED  subject=%r  sender=%r  "
                            "match=%s/%s=%r",
                            raw.subject, raw.sender,
                            cls.match_type, cls.match_field, cls.matched_value,
                        )

                        email_id = hashlib.sha256(raw.message_id.encode()).hexdigest()[:36] if raw.message_id else None
                        if not email_id:
                            logger.debug("_scan_emails: skipped — empty message_id on %r", raw.subject)
                            continue

                        existing = await email_repo.get(email_id, client_name)
                        if existing:
                            logger.debug("_scan_emails: already stored  id=%s  subject=%r", email_id, raw.subject)
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
                            attribution_reason=cls.match_type,
                            classification=cls,
                        )
                        await email_repo.upsert(scanned.model_dump(mode="json"))
                        total_new += 1
                        logger.info(
                            "_scan_emails: SAVED new email  id=%s  subject=%r  sender=%r  match=%s",
                            email_id, raw.subject, raw.sender, cls.match_type,
                        )

                        if progress_cb:
                            progress_cb({
                                "current_account": account.display_name,
                                "current_folder": folder,
                                "folder_status": "saving",
                                "totals_fetched": total_fetched,
                                "totals_matched": total_attributed,
                                "totals_new": total_new,
                                "message": f"Saved: {raw.subject[:60]}",
                            })

                        await self._update_memory_from_email(client_name, client_id, scanned)

                        if config.auto_draft and folder.lower() == "inbox":
                            await self._maybe_create_draft(
                                client_name, client_id, scanned, draft_repo, config
                            )

                        await self._publish_event(client_name, "new_email", email_id, f"New email: {raw.subject[:60]}")

                    logger.info(
                        "_scan_emails: folder %r/%r  fetched=%d attributed=%d skipped=%d",
                        account.display_name, folder,
                        len(raw_emails), attributed_in_folder, skipped_attribution,
                    )

                    if progress_cb:
                        progress_cb({
                            "current_account": account.display_name,
                            "current_folder": folder,
                            "folder_status": "done",
                            "folder_fetched": len(raw_emails),
                            "folder_matched": attributed_in_folder,
                            "totals_fetched": total_fetched,
                            "totals_matched": total_attributed,
                            "totals_new": total_new,
                            "message": f"{folder}: {len(raw_emails)} fetched, {attributed_in_folder} matched",
                        })

                except Exception as e:
                    logger.warning(
                        "_scan_emails: ERROR for %s/%s/%s: %s",
                        client_name, account.display_name, folder, e,
                        exc_info=True,
                    )
                    if progress_cb:
                        progress_cb({
                            "current_account": account.display_name,
                            "current_folder": folder,
                            "folder_status": "error",
                            "message": f"Error in {folder}: {e}",
                        })

        logger.info(
            "_scan_emails SUMMARY  client=%r  total_fetched=%d  attributed=%d  new_saved=%d",
            client_name, total_fetched, total_attributed, total_new,
        )

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
                    meeting_cls = self._meeting_matches(raw, config)
                    if meeting_cls is None:
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
                        global_id=raw.global_id or None,
                        my_response=raw.my_response,
                        transcript_summary=transcript_summary,
                        action_items_extracted=action_items,
                        classification=meeting_cls,
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

    def _attribute(self, raw: RawEmail, config: CommunicationConfig) -> Optional[EmailClassification]:
        """Return rich classification if this email belongs to the client, else None."""
        sender_lower = raw.sender.lower() if raw.sender else ""
        recipient_lowers = [r.lower() for r in raw.recipients if r]

        for domain in config.domains:
            d = domain.lower().lstrip("@")
            if f"@{d}" in sender_lower:
                return EmailClassification(match_type="domain_match", match_field="sender", matched_value=d)
            if any(f"@{d}" in r for r in recipient_lowers):
                return EmailClassification(match_type="domain_match", match_field="recipient", matched_value=d)

        for contact in config.contacts:
            c = contact.lower()
            if c == sender_lower:
                return EmailClassification(match_type="contact_match", match_field="sender", matched_value=contact)
            if c in recipient_lowers:
                return EmailClassification(match_type="contact_match", match_field="recipient", matched_value=contact)

        subject_lower = raw.subject.lower() if raw.subject else ""
        body_lower = raw.body.lower() if raw.body else ""
        for kw in config.keywords:
            kw_lower = kw.lower()
            in_subject = kw_lower in subject_lower
            in_body = kw_lower in body_lower
            if in_subject or in_body:
                if in_subject and in_body:
                    field = "subject_and_body"
                elif in_subject:
                    field = "subject"
                else:
                    field = "body"
                occurrences = body_lower.count(kw_lower) if in_body else 0
                pos = body_lower.find(kw_lower) if in_body else None
                return EmailClassification(
                    match_type="keyword_match",
                    match_field=field,
                    matched_value=kw,
                    keyword_occurrences=occurrences,
                    first_occurrence_position=pos,
                )

        return None

    def _meeting_matches(self, raw: RawCalendarItem, config: CommunicationConfig) -> Optional[MeetingClassification]:
        """Return classification if this meeting belongs to the client, else None."""
        attendee_emails = [a.email.lower() for a in raw.attendees if a.email]

        for domain in config.domains:
            d = domain.lower().lstrip("@")
            if any(f"@{d}" in e for e in attendee_emails):
                return MeetingClassification(match_type="domain_match", match_field="attendee", matched_value=d)

        for contact in config.contacts:
            if contact.lower() in attendee_emails:
                return MeetingClassification(match_type="contact_match", match_field="attendee", matched_value=contact)

        subject_lower = raw.subject.lower() if raw.subject else ""
        body_lower = raw.body.lower() if raw.body else ""
        for kw in config.keywords:
            kw_lower = kw.lower()
            in_subject = kw_lower in subject_lower
            in_body = kw_lower in body_lower
            if in_subject or in_body:
                if in_subject and in_body:
                    field = "subject_and_body"
                elif in_subject:
                    field = "subject"
                else:
                    field = "body"
                return MeetingClassification(match_type="keyword_match", match_field=field, matched_value=kw)

        return None

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

    async def _update_memory_from_email(self, client_name: str, client_id: str, email: ScannedEmail):
        try:
            repo = await self._manager.get_client_repo(client_id, "memories")
            memory = await repo.get(client_id, client_id)
            if memory is None:
                memory = {"id": client_id, "client_name": client_name}

            existing_emails = {s.get("email", "").lower() for s in memory.get("key_stakeholders", [])}
            stakeholders = memory.get("key_stakeholders", [])
            for addr in [email.sender] + email.recipients:
                if addr and "@" in addr and addr.lower() not in existing_emails:
                    name = addr.split("@")[0].replace(".", " ").replace("_", " ").title()
                    stakeholders.append({"name": name, "email": addr})
                    existing_emails.add(addr.lower())
            memory["key_stakeholders"] = stakeholders

            note: dict = {
                "date": email.received_at.isoformat(),
                "subject": email.subject[:80],
                "match_type": email.attribution_reason,
                "match_field": email.classification.match_field if email.classification else "",
                "matched_value": email.classification.matched_value if email.classification else "",
            }
            notes = memory.get("communication_notes", [])
            notes.append(note)
            memory["communication_notes"] = notes[-30:]
            memory["last_updated"] = datetime.now(timezone.utc).isoformat()
            await repo.upsert(memory)
        except Exception as e:
            logger.warning("Memory update from email failed: %s", e)

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
