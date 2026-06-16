# backend/app/services/outlook_inbox_search.py
"""
Cross-account Outlook inbox search.

Primary path:  win32com (local Outlook installation) via asyncio.to_thread.
Fallback path: Microsoft Graph API (requires GraphAPIService to be provided).

Returns raw email dicts suitable for re-ranking and client attribution in the
inbox_search API layer.  No client attribution logic lives here.
"""
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def _hash_id(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:36]


# ---------------------------------------------------------------------------
# win32com (synchronous — called via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _search_win32(queries: list[str], since: datetime, filters: dict) -> list[dict]:
    """Synchronous win32com search across all accounts and all non-junk folders."""
    try:
        import pythoncom
        import win32com.client  # noqa: F401 — availability check
    except ImportError:
        return []

    try:
        import pythoncom
        pythoncom.CoInitialize()
    except Exception:
        return []

    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        ns = outlook.GetNamespace("MAPI")
    except Exception as e:
        logger.warning("Outlook not available: %s", e)
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass
        return []

    since_str = since.strftime("%m/%d/%Y %H:%M %p")
    results: dict[str, dict] = {}

    _SKIP_FOLDERS = {"junk", "spam", "trash", "deleted", "outbox", "sync issues"}

    def _collect_folder(folder) -> None:
        try:
            items = folder.Items
            items.Sort("[ReceivedTime]", True)

            # --- build DASL restriction ---
            date_filter = f"[ReceivedTime] >= '{since_str}'"
            if filters.get("has_attachment") is True:
                date_filter += " AND [Attachments] > 0"
            if filters.get("date_to"):
                date_filter += f" AND [ReceivedTime] <= '{filters['date_to']}'"

            text_parts: list[str] = []
            for q in queries:
                q_escaped = q.replace("'", "''")
                text_parts.append(
                    f"(@SQL=\"urn:schemas:httpmail:subject\" LIKE '%{q_escaped}%' "
                    f"OR \"urn:schemas:httpmail:textdescription\" LIKE '%{q_escaped}%' "
                    f"OR \"urn:schemas:httpmail:displayfrom\" LIKE '%{q_escaped}%')"
                )
            combined = (
                f"({date_filter}) AND ({' OR '.join(text_parts)})"
                if text_parts
                else date_filter
            )

            restricted = items.Restrict(combined)
            for item in restricted:
                try:
                    if item.Class != 43:  # 43 = olMail
                        continue

                    sender_email = ""
                    sender_name = ""
                    try:
                        sender_email = item.SenderEmailAddress or ""
                        sender_name = item.SenderName or ""
                    except Exception:
                        pass

                    # Sender filter checks
                    if filters.get("sender_name"):
                        sn = filters["sender_name"].lower()
                        if sn not in sender_name.lower() and sn not in sender_email.lower():
                            continue
                    if filters.get("sender_domain"):
                        if filters["sender_domain"].lower() not in sender_email.lower():
                            continue

                    entry_id = ""
                    try:
                        entry_id = item.EntryID or ""
                    except Exception:
                        pass
                    uid = (
                        _hash_id(entry_id)
                        if entry_id
                        else _hash_id(f"{sender_email}{item.Subject}{item.ReceivedTime}")
                    )
                    if uid in results:
                        continue

                    body_preview = ""
                    try:
                        body_preview = (
                            (item.Body or "")[:500]
                            .replace("\r\n", " ")
                            .replace("\n", " ")
                            .strip()
                        )
                    except Exception:
                        pass

                    received = None
                    try:
                        received = item.ReceivedTime.isoformat()
                    except Exception:
                        pass

                    account_name = ""
                    try:
                        account_name = folder.Store.DisplayName
                    except Exception:
                        pass

                    has_attachment = False
                    try:
                        has_attachment = item.Attachments.Count > 0
                    except Exception:
                        pass

                    results[uid] = {
                        "id": uid,
                        "subject": item.Subject or "",
                        "sender": sender_email,
                        "sender_name": sender_name,
                        "recipients": [],
                        "body_preview": body_preview,
                        "received_at": received,
                        "folder": folder.Name,
                        "account": account_name,
                        "has_attachment": has_attachment,
                        "attachment_names": [],
                        "client_name": None,
                        "client_path": None,
                    }
                except Exception as item_err:
                    logger.debug("Skipping item: %s", item_err)
        except Exception as folder_err:
            logger.debug("Skipping folder %s: %s", getattr(folder, "Name", "?"), folder_err)

    def _walk_folder(folder) -> None:
        _collect_folder(folder)
        try:
            for sub in folder.Folders:
                _walk_folder(sub)
        except Exception:
            pass

    try:
        for account in ns.Accounts:
            try:
                store = account.DeliveryStore
                root = store.GetRootFolder()
                for folder in root.Folders:
                    folder_lower = folder.Name.lower()
                    if any(x in folder_lower for x in _SKIP_FOLDERS):
                        continue
                    if filters.get("folder") and filters["folder"].lower() not in folder_lower:
                        continue
                    _walk_folder(folder)
            except Exception as acct_err:
                logger.debug("Skipping account: %s", acct_err)
    except Exception as e:
        logger.warning("win32com search failed: %s", e)
    finally:
        try:
            import pythoncom
            pythoncom.CoUninitialize()
        except Exception:
            pass

    return list(results.values())


# ---------------------------------------------------------------------------
# Graph API fallback (async)
# ---------------------------------------------------------------------------

async def _search_graph(
    queries: list[str],
    since: datetime,
    filters: dict,
    graph_service,
) -> list[dict]:
    """Graph API search fallback using GraphAPIService._get_token()."""
    if graph_service is None:
        return []

    results: dict[str, dict] = {}
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    for q in queries:
        try:
            token = await graph_service._get_token()
            import aiohttp

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            params: dict = {
                "$search": f'"{q}"',
                "$top": "50",
                "$select": (
                    "id,subject,from,toRecipients,bodyPreview,"
                    "receivedDateTime,parentFolderId,hasAttachments"
                ),
                "$filter": f"receivedDateTime ge {since_str}",
                "$orderby": "receivedDateTime desc",
            }
            url = "https://graph.microsoft.com/v1.0/me/messages"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.debug("Graph search returned %d for query %r", resp.status, q)
                        continue
                    data = await resp.json()
                    for msg in data.get("value", []):
                        uid = _hash_id(msg["id"])
                        if uid in results:
                            continue
                        sender_addr = (
                            msg.get("from", {}).get("emailAddress", {}).get("address", "")
                        )
                        sender_name = (
                            msg.get("from", {}).get("emailAddress", {}).get("name", "")
                        )
                        if filters.get("sender_name"):
                            if filters["sender_name"].lower() not in sender_name.lower():
                                continue
                        if filters.get("sender_domain"):
                            if filters["sender_domain"].lower() not in sender_addr.lower():
                                continue
                        results[uid] = {
                            "id": uid,
                            "subject": msg.get("subject", ""),
                            "sender": sender_addr,
                            "sender_name": sender_name,
                            "recipients": [
                                r["emailAddress"]["address"]
                                for r in msg.get("toRecipients", [])
                            ],
                            "body_preview": msg.get("bodyPreview", ""),
                            "received_at": msg.get("receivedDateTime"),
                            "folder": "",
                            "account": "",
                            "has_attachment": msg.get("hasAttachments", False),
                            "attachment_names": [],
                            "client_name": None,
                            "client_path": None,
                        }
        except Exception as e:
            logger.debug("Graph search for %r failed: %s", q, e)

    return list(results.values())


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def search_outlook_inbox(
    queries: list[str],
    filters: dict,
    days: int = 90,
    graph_service=None,
) -> list[dict]:
    """Search the Outlook inbox using expanded queries.

    Tries win32com first (local Outlook); falls back to Graph API if win32com
    returns nothing or is unavailable.

    Args:
        queries: Expanded query strings from EmailQueryAnalyzer.
        filters: Dict with optional keys sender_name, sender_domain,
                 date_from, date_to, folder, has_attachment.
        days: How far back to search (default 90).
        graph_service: Optional GraphAPIService instance for fallback.

    Returns:
        List of raw email dicts (no client attribution, no relevance scores).
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    raw = await asyncio.to_thread(_search_win32, queries, since, filters)
    if not raw:
        raw = await _search_graph(queries, since, filters, graph_service)

    return raw
