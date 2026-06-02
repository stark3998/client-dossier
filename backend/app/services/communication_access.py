# backend/app/services/communication_access.py
"""
Unified communication access layer.
win32com (local Outlook) is tried first; falls back to Graph API for email/calendar.
Teams features always go through Graph API.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.models.communication import RawCalendarItem, RawEmail
from app.services.graph_api_service import GraphAPIService
from app.services.outlook_win32 import OutlookWin32Service

logger = logging.getLogger(__name__)


class CommunicationAccess:
    def __init__(self, win32: OutlookWin32Service, graph: GraphAPIService):
        self._win32 = win32
        self._graph = graph

    async def get_accounts(self) -> list[str]:
        if self._win32.is_available():
            return await asyncio.to_thread(self._win32.get_accounts)
        if self._graph.is_configured():
            return [self._graph._user_email]
        return []

    async def get_folders(self, account: str) -> list[str]:
        if self._win32.is_available():
            return await asyncio.to_thread(self._win32.get_folders, account)
        # Graph has well-known folder names
        return ["Inbox", "Sent Items", "Drafts", "Deleted Items"]

    async def get_emails(
        self,
        account: str,
        folder: str,
        since: datetime,
    ) -> list[RawEmail]:
        if self._win32.is_available():
            return await asyncio.to_thread(
                self._win32.get_emails, account, folder, since
            )
        if self._graph.is_configured():
            folder_id = "SentItems" if "sent" in folder.lower() else "Inbox"
            return await self._graph.get_emails(folder=folder_id, since=since)
        return []

    async def get_calendar_events(
        self,
        account: str,
        since: datetime,
        until: datetime,
    ) -> list[RawCalendarItem]:
        if self._win32.is_available():
            return await asyncio.to_thread(
                self._win32.get_calendar_items, account, since, until
            )
        if self._graph.is_configured():
            return await self._graph.get_calendar_events(since=since, until=until)
        return []

    async def create_draft(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: Optional[list[str]] = None,
    ) -> Optional[str]:
        """Write draft to Outlook Drafts folder. Returns EntryID or None."""
        if self._win32.is_available():
            return await asyncio.to_thread(
                self._win32.create_draft, to, subject, body, cc or []
            )
        logger.warning("Cannot push draft: win32com unavailable and Graph draft push not implemented")
        return None

    async def update_draft(self, entry_id: str, body: str, subject: Optional[str] = None) -> bool:
        if self._win32.is_available():
            await asyncio.to_thread(self._win32.update_draft, entry_id, body, subject)
            return True
        return False

    # Teams — always via Graph

    async def get_joined_teams(self) -> list[dict]:
        return await self._graph.get_joined_teams()

    async def get_teams_channels(self, team_id: str) -> list[dict]:
        return await self._graph.get_teams_channels(team_id)

    async def get_channel_messages(
        self, team_id: str, channel_id: str, since: Optional[datetime] = None
    ) -> list[dict]:
        return await self._graph.get_channel_messages(team_id, channel_id, since)

    async def get_meeting_transcript(self, online_meeting_id: str) -> Optional[str]:
        return await self._graph.get_meeting_transcript(online_meeting_id)
