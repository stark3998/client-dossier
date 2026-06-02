# backend/app/api/communication.py
import hashlib
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.models.communication import CommunicationConfig, DraftReply

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/communication", tags=["communication"])
ws_router = APIRouter(tags=["communication-ws"])


def _client_id(client_name: str) -> str:
    return client_name.lower().replace(" ", "-")


async def _get_repo(client_name: str, container: str):
    from app.dependencies import get_cosmos_manager
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Cosmos not initialized")
    return await manager.get_client_repo(_client_id(client_name), container)


# -- Outlook accounts (for config UI) ----------------------------------------

@router.get("/{client_name}/accounts")
async def list_outlook_accounts(client_name: str):
    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        return {"accounts": [], "source": "unavailable"}
    accounts = await access.get_accounts()
    return {"accounts": accounts}


@router.get("/{client_name}/accounts/{account_name}/folders")
async def list_outlook_folders(client_name: str, account_name: str):
    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        return {"folders": []}
    folders = await access.get_folders(account_name)
    return {"folders": folders}


# -- Config -------------------------------------------------------------------

@router.get("/{client_name}/config")
async def get_config(client_name: str):
    repo = await _get_repo(client_name, "communication_config")
    raw = await repo.get(_client_id(client_name), _client_id(client_name))
    if not raw:
        return {"config": None}
    return {"config": raw}


@router.put("/{client_name}/config")
async def update_config(client_name: str, body: CommunicationConfig):
    body.id = _client_id(client_name)
    body.client_name = client_name
    body.updated_at = datetime.now(timezone.utc)
    repo = await _get_repo(client_name, "communication_config")
    result = await repo.upsert(body.model_dump(mode="json"))
    return result


# -- Manual scan trigger ------------------------------------------------------

@router.post("/{client_name}/scan")
async def trigger_scan(client_name: str, background_tasks: BackgroundTasks):
    from app.dependencies import get_communication_scanner
    scanner = get_communication_scanner()
    if scanner is None:
        raise HTTPException(status_code=503, detail="Communication scanner not initialized")

    async def _run():
        config = await scanner._get_config(client_name)
        if config:
            await scanner.scan_client(client_name, config)

    background_tasks.add_task(_run)
    return {"status": "scan_triggered", "client": client_name}


# -- Emails -------------------------------------------------------------------

@router.get("/{client_name}/emails")
async def list_emails(
    client_name: str,
    days: int = Query(default=7, ge=1, le=90),
    search: Optional[str] = Query(default=None),
    folder: Optional[str] = Query(default=None),
):
    repo = await _get_repo(client_name, "emails")
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    items = await repo.query(
        "SELECT c.id, c.subject, c.sender, c.recipients, c.body_preview, "
        "c.received_at, c.folder, c.account, c.attribution_reason, c.classification, "
        "c.has_draft_reply, c.has_attachment, c.attachment_names "
        "FROM c WHERE c.received_at >= @since ORDER BY c.received_at DESC",
        [{"name": "@since", "value": since}],
    )
    # Backward-compat shim: old records have attribution_reason string but no classification object
    for item in items:
        if item.get("classification") is None and item.get("attribution_reason"):
            item["classification"] = {"match_type": item["attribution_reason"], "match_field": "unknown", "matched_value": ""}

    if search:
        sl = search.lower()
        items = [
            i for i in items
            if sl in (i.get("subject") or "").lower()
            or sl in (i.get("sender") or "").lower()
            or sl in (i.get("body_preview") or "").lower()
        ]
    if folder:
        items = [i for i in items if (i.get("folder") or "").lower() == folder.lower()]
    return {"emails": items, "count": len(items)}


@router.get("/{client_name}/emails/{email_id}")
async def get_email(client_name: str, email_id: str):
    repo = await _get_repo(client_name, "emails")
    item = await repo.get(email_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Email not found")
    return item


# -- Meetings -----------------------------------------------------------------

@router.get("/{client_name}/meetings")
async def list_meetings(
    client_name: str,
    days: int = Query(default=30, ge=1, le=365),
    upcoming_only: bool = Query(default=False),
):
    repo = await _get_repo(client_name, "meetings")
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    items = await repo.query(
        "SELECT c.id, c.client_name, c.subject, c.organizer, c.attendees, c.start_time, c.end_time, "
        "c.location, c.is_teams_meeting, c.my_response, c.global_id, c.classification, "
        "c.transcript_summary, c.action_items_extracted "
        "FROM c WHERE c.start_time >= @since ORDER BY c.start_time DESC",
        [{"name": "@since", "value": since}],
    )
    if upcoming_only:
        now = datetime.now(timezone.utc).isoformat()
        items = [i for i in items if (i.get("start_time") or "") >= now]
    return {"meetings": items, "count": len(items)}


@router.get("/{client_name}/meetings/{meeting_id}")
async def get_meeting(client_name: str, meeting_id: str):
    repo = await _get_repo(client_name, "meetings")
    item = await repo.get(meeting_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return item


@router.post("/{client_name}/meetings/{meeting_id}/fetch-transcript")
async def fetch_transcript(client_name: str, meeting_id: str, background_tasks: BackgroundTasks):
    """Trigger a live transcript fetch for a completed Teams meeting."""
    from app.dependencies import get_communication_access, get_cosmos_manager
    access = get_communication_access()
    if access is None:
        raise HTTPException(status_code=503, detail="Communication access not initialized")

    async def _run():
        repo = await get_cosmos_manager().get_client_repo(_client_id(client_name), "meetings")
        meeting = await repo.get(meeting_id, client_name)
        if not meeting:
            return
        oid = meeting.get("online_meeting_id")
        if not oid:
            return
        from app.dependencies import get_communication_scanner
        scanner = get_communication_scanner()
        if scanner:
            summary = await scanner._fetch_transcript_summary(oid, client_name)
            if summary:
                meeting["transcript_summary"] = summary
                meeting["action_items_extracted"] = await scanner._extract_action_items(summary)
                await repo.upsert(meeting)

    background_tasks.add_task(_run)
    return {"status": "transcript_fetch_triggered"}


@router.post("/{client_name}/meetings/{meeting_id}/respond")
async def respond_to_meeting(client_name: str, meeting_id: str, body: dict):
    """Accept, decline, or tentatively accept a meeting invite via Outlook.

    body: {"response": "accept" | "decline" | "tentative"}
    """
    response = body.get("response", "")
    if response not in ("accept", "decline", "tentative"):
        raise HTTPException(status_code=400, detail="response must be 'accept', 'decline', or 'tentative'")

    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        raise HTTPException(status_code=503, detail="Communication access not initialized")

    repo = await _get_repo(client_name, "meetings")
    meeting = await repo.get(meeting_id, client_name)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    global_id = meeting.get("global_id")
    if not global_id:
        raise HTTPException(status_code=422, detail="Meeting has no Outlook entry ID — cannot respond via win32com")

    success = await access.respond_to_meeting(global_id, response)
    if not success:
        raise HTTPException(status_code=503, detail="Outlook not available for RSVP")

    response_label = {"accept": "accepted", "decline": "declined", "tentative": "tentative"}[response]
    meeting["my_response"] = response_label
    await repo.upsert(meeting)
    return {"status": "responded", "response": response_label, "meeting_id": meeting_id}


# -- Draft Replies ------------------------------------------------------------

@router.get("/{client_name}/drafts")
async def list_drafts(
    client_name: str,
    status: Optional[str] = Query(default=None),
):
    repo = await _get_repo(client_name, "draft_replies")
    if status:
        items = await repo.query(
            "SELECT * FROM c WHERE c.status = @status ORDER BY c.created_at DESC",
            [{"name": "@status", "value": status}],
        )
    else:
        items = await repo.query(
            "SELECT * FROM c WHERE c.status != 'discarded' ORDER BY c.created_at DESC",
            [],
        )
    return {"drafts": items, "count": len(items)}


@router.get("/{client_name}/drafts/{draft_id}")
async def get_draft(client_name: str, draft_id: str):
    repo = await _get_repo(client_name, "draft_replies")
    item = await repo.get(draft_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")
    return item


@router.put("/{client_name}/drafts/{draft_id}")
async def update_draft(client_name: str, draft_id: str, body: dict):
    repo = await _get_repo(client_name, "draft_replies")
    item = await repo.get(draft_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")
    allowed = {"subject", "body", "to", "cc"}
    for k, v in body.items():
        if k in allowed:
            item[k] = v
    item["status"] = "edited"
    return await repo.upsert(item)


@router.post("/{client_name}/drafts/{draft_id}/approve")
async def approve_draft(client_name: str, draft_id: str):
    """Push the draft to Outlook Drafts folder via win32com."""
    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        raise HTTPException(status_code=503, detail="Communication access not initialized")

    repo = await _get_repo(client_name, "draft_replies")
    item = await repo.get(draft_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")

    entry_id = await access.create_draft(
        to=item.get("to", []),
        subject=item.get("subject", ""),
        body=item.get("body", ""),
        cc=item.get("cc") or [],
    )
    item["status"] = "pushed_to_outlook"
    item["pushed_at"] = datetime.now(timezone.utc).isoformat()
    item["outlook_entry_id"] = entry_id
    result = await repo.upsert(item)
    return {"status": "pushed", "outlook_entry_id": entry_id, "draft": result}


@router.post("/{client_name}/drafts/{draft_id}/feedback")
async def submit_draft_feedback(client_name: str, draft_id: str, body: dict):
    """Save feedback on a draft and update agent memory with the insight."""
    feedback_text = body.get("feedback", "")
    if not feedback_text:
        raise HTTPException(status_code=400, detail="feedback field required")

    repo = await _get_repo(client_name, "draft_replies")
    item = await repo.get(draft_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")
    item["feedback"] = feedback_text
    await repo.upsert(item)

    # Update memory with the feedback insight
    try:
        from app.dependencies import get_cosmos_manager
        manager = get_cosmos_manager()
        if manager:
            mem_repo = await manager.get_client_repo(_client_id(client_name), "memories")
            memory = await mem_repo.get(_client_id(client_name), _client_id(client_name))
            if memory is None:
                memory = {"id": _client_id(client_name), "client_name": client_name}
            notes = memory.get("communication_notes", [])
            notes.append(f"Draft feedback ({item.get('subject', '')}): {feedback_text}")
            memory["communication_notes"] = notes[-20:]  # keep last 20
            memory["last_updated"] = datetime.now(timezone.utc).isoformat()
            await mem_repo.upsert(memory)
    except Exception as e:
        logger.warning("Memory update from feedback failed: %s", e)

    return {"status": "feedback_saved"}


@router.post("/{client_name}/drafts")
async def create_draft(client_name: str, body: dict):
    """Manually create a draft reply for an email.

    body: {"email_id": str}
    Fetches thread context (up to 3 prior emails) and generates a reply via the AI kernel.
    """
    email_id = body.get("email_id")
    if not email_id:
        raise HTTPException(status_code=400, detail="email_id required")

    email_repo = await _get_repo(client_name, "emails")
    draft_repo = await _get_repo(client_name, "draft_replies")

    email = await email_repo.get(email_id, client_name)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    # Check for existing draft for this email
    existing = await draft_repo.query(
        "SELECT * FROM c WHERE c.email_id = @eid AND c.status != 'discarded'",
        [{"name": "@eid", "value": email_id}],
    )
    if existing:
        return existing[0]

    # Gather thread context (last 3 emails in same thread, excluding this one)
    thread_id = email.get("thread_id")
    thread_context = ""
    if thread_id:
        thread_emails = await email_repo.query(
            "SELECT c.sender, c.subject, c.body_preview, c.received_at "
            "FROM c WHERE c.thread_id = @tid AND c.id != @eid ORDER BY c.received_at DESC OFFSET 0 LIMIT 3",
            [{"name": "@tid", "value": thread_id}, {"name": "@eid", "value": email_id}],
        )
        if thread_emails:
            thread_context = "\n\n---Prior messages in thread---\n" + "\n\n".join(
                f"From: {e.get('sender','')}\n{e.get('body_preview','')[:300]}" for e in thread_emails
            )

    from app.dependencies import get_communication_scanner
    scanner = get_communication_scanner()

    from app.models.communication import ScannedEmail
    try:
        email_model = ScannedEmail(**email)
    except Exception:
        raise HTTPException(status_code=422, detail="Could not parse email record")

    # Generate body — if scanner has kernel use AI, else use fallback
    if scanner and scanner._kernel:
        try:
            from semantic_kernel.contents import ChatHistory
            chat = ChatHistory()
            chat.add_system_message(
                f"You are a professional consultant. Draft a concise, professional email reply "
                f"for the client '{client_name}'. Keep it brief (3-5 sentences). "
                f"Do not include subject line. Start with a greeting."
            )
            chat.add_user_message(
                f"Original email from {email.get('sender','')}:\n"
                f"Subject: {email.get('subject','')}\n\n"
                f"{email.get('body_full') or email.get('body_preview','')}"
                f"{thread_context}"
            )
            from app.agent.kernel import get_execution_settings
            result = await scanner._kernel.invoke_prompt(
                prompt="{{$chat_history}}",
                chat_history=chat,
                settings=get_execution_settings(),
            )
            draft_body = str(result)
        except Exception as e:
            logger.warning("Draft generation failed: %s", e)
            draft_body = f"Thank you for your email. We will review and respond shortly.\n\n[Auto-generated draft for: {email.get('subject','')}]"
    else:
        draft_body = f"[Auto-draft] Thank you for your email regarding: {email.get('subject','')}\n\nPlease review and edit this draft before sending."

    draft = DraftReply(
        client_name=client_name,
        email_id=email_id,
        subject=f"Re: {email.get('subject', '')}",
        to=[email.get("sender", "")] if email.get("sender") else [],
        body=draft_body,
    )
    result = await draft_repo.upsert(draft.model_dump(mode="json"))
    return result


@router.delete("/{client_name}/drafts/{draft_id}")
async def discard_draft(client_name: str, draft_id: str):
    repo = await _get_repo(client_name, "draft_replies")
    item = await repo.get(draft_id, client_name)
    if not item:
        raise HTTPException(status_code=404, detail="Draft not found")
    item["status"] = "discarded"
    await repo.upsert(item)
    return {"status": "discarded"}


# -- Teams channels -----------------------------------------------------------

@router.get("/{client_name}/teams")
async def list_teams(client_name: str):
    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        return {"teams": []}
    teams = await access.get_joined_teams()
    return {"teams": teams}


@router.get("/{client_name}/teams/{team_id}/channels")
async def list_channels(client_name: str, team_id: str):
    from app.dependencies import get_communication_access
    access = get_communication_access()
    if access is None:
        return {"channels": []}
    channels = await access.get_teams_channels(team_id)
    return {"channels": channels}


@router.get("/{client_name}/teams/{team_id}/channels/{channel_id}/messages")
async def get_channel_messages(
    client_name: str,
    team_id: str,
    channel_id: str,
    days: int = Query(default=7, ge=1, le=30),
):
    from app.dependencies import get_communication_access
    from datetime import timedelta
    access = get_communication_access()
    if access is None:
        return {"messages": []}
    since = datetime.now(timezone.utc) - timedelta(days=days)
    messages = await access.get_channel_messages(team_id, channel_id, since)
    return {"messages": messages, "count": len(messages)}


# -- Thread grouping ----------------------------------------------------------

_STRIP_PREFIX = re.compile(r"^(re|fwd?|aw|sv|tr):\s*", re.IGNORECASE)

def _normalize_subject(subject: str) -> str:
    s = subject.strip()
    while True:
        new_s = _STRIP_PREFIX.sub("", s).strip()
        if new_s == s:
            break
        s = new_s
    return s.lower()

def _thread_key(email: dict) -> str:
    """Derive a stable thread key from thread_id or normalized subject."""
    tid = email.get("thread_id")
    if tid:
        return tid
    norm = _normalize_subject(email.get("subject", ""))
    return "subj_" + hashlib.sha256(norm.encode()).hexdigest()[:16]


@router.get("/{client_name}/threads")
async def list_threads(
    client_name: str,
    days: int = Query(default=14, ge=1, le=90),
    search: Optional[str] = Query(default=None),
):
    """Return emails grouped into threads, sorted by latest message date."""
    from datetime import timedelta
    repo = await _get_repo(client_name, "emails")
    draft_repo = await _get_repo(client_name, "draft_replies")

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    emails = await repo.query(
        "SELECT c.id, c.subject, c.sender, c.recipients, c.body_preview, "
        "c.received_at, c.thread_id, c.has_draft_reply, c.attribution_reason, c.classification, "
        "c.has_attachment, c.folder, c.account "
        "FROM c WHERE c.received_at >= @since ORDER BY c.received_at DESC",
        [{"name": "@since", "value": since}],
    )
    for e in emails:
        if e.get("classification") is None and e.get("attribution_reason"):
            e["classification"] = {"match_type": e["attribution_reason"], "match_field": "unknown", "matched_value": ""}

    if search:
        sl = search.lower()
        emails = [
            e for e in emails
            if sl in (e.get("subject") or "").lower()
            or sl in (e.get("sender") or "").lower()
            or sl in (e.get("body_preview") or "").lower()
        ]

    # Fetch pending draft counts for badge
    drafts = await draft_repo.query(
        "SELECT c.email_id FROM c WHERE c.status = 'pending_review' OR c.status = 'edited'",
        [],
    )
    draft_email_ids = {d["email_id"] for d in drafts if d.get("email_id")}

    # Group by thread key
    thread_map: dict[str, dict] = {}
    thread_emails: dict[str, list[dict]] = defaultdict(list)

    for email in emails:
        key = _thread_key(email)
        thread_emails[key].append(email)
        if key not in thread_map:
            thread_map[key] = {
                "thread_key": key,
                "subject": _normalize_subject(email.get("subject", "")),
                "latest_date": email.get("received_at", ""),
                "attribution_reason": email.get("attribution_reason", ""),
            }
        else:
            # Keep latest date
            if email.get("received_at", "") > thread_map[key]["latest_date"]:
                thread_map[key]["latest_date"] = email.get("received_at", "")

    threads = []
    for key, meta in thread_map.items():
        msgs = thread_emails[key]
        participants = list({e.get("sender", "") for e in msgs if e.get("sender")})
        has_draft = any(e["id"] in draft_email_ids for e in msgs)
        threads.append({
            **meta,
            "message_count": len(msgs),
            "participants": participants[:5],
            "has_draft_reply": has_draft or any(e.get("has_draft_reply") for e in msgs),
            "has_attachment": any(e.get("has_attachment") for e in msgs),
            "latest_sender": msgs[0].get("sender", "") if msgs else "",
        })

    threads.sort(key=lambda t: t["latest_date"], reverse=True)
    return {"threads": threads, "count": len(threads)}


@router.get("/{client_name}/threads/{thread_key}")
async def get_thread(client_name: str, thread_key: str):
    """Return all emails in a thread ordered chronologically."""
    repo = await _get_repo(client_name, "emails")
    all_emails = await repo.query("SELECT * FROM c ORDER BY c.received_at ASC", [])

    thread_emails = [e for e in all_emails if _thread_key(e) == thread_key]
    if not thread_emails:
        raise HTTPException(status_code=404, detail="Thread not found")

    return {
        "thread_key": thread_key,
        "subject": _normalize_subject(thread_emails[0].get("subject", "")),
        "emails": thread_emails,
        "message_count": len(thread_emails),
    }


# -- Thread AI Insight (WebSocket streaming) -----------------------------------

INSIGHT_SYSTEM_PROMPT = """You are an expert consulting intelligence assistant.
Analyse the provided email thread and generate a concise, structured insight for a consultant.

Your response must follow this exact markdown structure:

## Summary
2-3 sentences capturing what this conversation is about and its current status.

## Action Items
- List each action item (who needs to do what)
- Mark items that are time-sensitive with ⚡

## Risks & Concerns
- Any flags, blockers, or concerns detected in the thread
- If none, write "None identified"

## Suggested Response Approach
1-2 sentences on the recommended tone and key points to address in any reply.

## Key Topics
Comma-separated list of 3-6 key topics.

Be concise. Use the related documents (if provided) to add context and mention relevant project artifacts."""


@ws_router.websocket("/ws/communication/{client_name}/threads/{thread_key}/insight")
async def ws_thread_insight(websocket: WebSocket, client_name: str, thread_key: str):
    await websocket.accept()

    settings = None
    try:
        from app.config import get_settings
        settings = get_settings()
    except Exception:
        pass

    if settings and not settings.LOCAL_MODE:
        token = websocket.query_params.get("token", "")
        if not token:
            await websocket.close(code=4001, reason="Missing token")
            return

    try:
        from app.dependencies import get_planner, get_cosmos_manager
        planner = get_planner()
        manager = get_cosmos_manager()
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})
        await websocket.close()
        return

    if planner is None or manager is None:
        await websocket.send_json({"type": "error", "message": "Agent not initialized"})
        await websocket.close()
        return

    try:
        # 1. Fetch thread emails from Cosmos
        client_id = client_name.lower().replace(" ", "-")
        email_repo = await manager.get_client_repo(client_id, "emails")
        all_emails = await email_repo.query("SELECT * FROM c ORDER BY c.received_at ASC", [])
        thread_emails = [e for e in all_emails if _thread_key(e) == thread_key]

        if not thread_emails:
            await websocket.send_json({"type": "error", "message": "Thread not found"})
            await websocket.close()
            return

        # 2. Build thread context string
        subject = _normalize_subject(thread_emails[0].get("subject", ""))
        participants = list({e.get("sender", "") for e in thread_emails if e.get("sender")})
        thread_text_parts = [f"Subject: {subject}", f"Participants: {', '.join(participants)}", "---"]
        for e in thread_emails:
            dt = e.get("received_at", "")[:10]
            sender = e.get("sender", "unknown")
            body = (e.get("body_full") or e.get("body_preview") or "")[:600]
            thread_text_parts.append(f"\n[{dt}] From: {sender}\n{body}")
        thread_context = "\n".join(thread_text_parts)

        # 3. Search for related knowledge-base documents via service layer
        search_query = f"{subject} {thread_emails[-1].get('body_preview', '')[:200]}"
        search_context = ""
        sources_for_event: list[dict] = []
        try:
            from app.dependencies import get_search_service, get_embedding_service
            search_svc = get_search_service()
            embed_svc = get_embedding_service()
            if search_svc and embed_svc:
                vector = await embed_svc.embed_query(search_query)
                filters = f"client_name eq '{client_name}'"
                candidates = await search_svc.hybrid_search(
                    query_text=search_query, query_vector=vector, top=18, filters=filters
                )
                results = search_svc.rerank(search_query, candidates, top_k=6)
                if results:
                    search_context = "\n\n## Related Documents\n"
                    for doc in results:
                        search_context += f"- {doc.get('file_path', '')}: {doc.get('content', '')[:300]}\n"
                        sources_for_event.append({
                            "file_path": doc.get("file_path", ""),
                            "section_title": doc.get("section_title"),
                            "page_number": doc.get("page_number"),
                            "excerpt": doc.get("content", "")[:200],
                            "score": doc.get("score", 0),
                        })
        except Exception as e:
            logger.warning("Search for thread insight failed: %s", e)

        # 4. Stream AI insight via planner
        from semantic_kernel.contents import ChatHistory
        chat_history = ChatHistory()
        chat_history.add_system_message(INSIGHT_SYSTEM_PROMPT)

        user_message = f"## Email Thread\n{thread_context}\n{search_context}\n\nGenerate the structured insight."

        content_parts: list[str] = []

        async for event in planner.stream_response(
            chat_history=chat_history,
            user_message=user_message,
            client_name=client_name,
        ):
            payload = event.model_dump(exclude_none=True)
            if payload.get("type") == "token":
                content_parts.append(payload.get("content", ""))
            await websocket.send_json(payload)

        # Send source chips from search results (in addition to any search plugin sources)
        for src in sources_for_event:
            await websocket.send_json({"type": "source", "source": src})

        # 5. Cache insight back to Cosmos on the most recent email in thread
        if content_parts:
            insight_text = "".join(content_parts)
            latest = thread_emails[-1]
            latest["ai_insight"] = insight_text
            latest["ai_insight_sources"] = sources_for_event
            latest["ai_insight_at"] = datetime.now(timezone.utc).isoformat()
            try:
                await email_repo.upsert(latest)
            except Exception as e:
                logger.warning("Failed to cache thread insight: %s", e)

    except WebSocketDisconnect:
        logger.info("Thread insight WebSocket disconnected")
    except Exception as e:
        logger.error("Thread insight WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
