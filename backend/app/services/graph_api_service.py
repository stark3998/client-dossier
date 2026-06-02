# backend/app/services/graph_api_service.py
"""
Microsoft Graph API client for emails, calendar events, and Teams data.
Used as fallback when win32com is unavailable, and as primary for Teams features.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.communication import MeetingAttendee, RawCalendarItem, RawEmail

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphAPIService:
    def __init__(self, client_id: str, tenant_id: str, client_secret: str, user_email: str):
        self._client_id = client_id
        self._tenant_id = tenant_id
        self._client_secret = client_secret
        self._user_email = user_email
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def is_configured(self) -> bool:
        return bool(self._client_id and self._tenant_id and self._client_secret and self._user_email)

    async def _get_token(self) -> str:
        now = datetime.now(timezone.utc)
        if self._token and self._token_expiry and now < self._token_expiry:
            return self._token

        import aiohttp
        url = f"https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as resp:
                resp.raise_for_status()
                body = await resp.json()

        self._token = body["access_token"]
        from datetime import timedelta
        self._token_expiry = now + timedelta(seconds=body.get("expires_in", 3600) - 60)
        return self._token

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        import aiohttp
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{GRAPH_BASE}{path}", headers=headers, params=params) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def get_emails(
        self,
        folder: str = "Inbox",
        since: Optional[datetime] = None,
    ) -> list[RawEmail]:
        if not self.is_configured():
            return []
        try:
            folder_path = f"/users/{self._user_email}/mailFolders/{folder}/messages"
            params: dict = {
                "$top": "100",
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,toRecipients,ccRecipients,body,receivedDateTime,hasAttachments,attachments,conversationId",
            }
            if since:
                params["$filter"] = f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

            data = await self._get(folder_path, params)
            return [self._msg_to_raw(m, folder) for m in data.get("value", [])]
        except Exception as e:
            logger.warning("Graph get_emails failed: %s", e)
            return []

    async def get_calendar_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> list[RawCalendarItem]:
        if not self.is_configured():
            return []
        try:
            path = f"/users/{self._user_email}/calendarView"
            params: dict = {
                "$top": "100",
                "$select": "subject,organizer,attendees,start,end,location,body,isOnlineMeeting,onlineMeeting,responseStatus",
                "startDateTime": (since or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endDateTime": (until or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            data = await self._get(path, params)
            return [self._event_to_raw(e) for e in data.get("value", [])]
        except Exception as e:
            logger.warning("Graph get_calendar_events failed: %s", e)
            return []

    async def get_teams_channels(self, team_id: str) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            data = await self._get(f"/teams/{team_id}/channels")
            return data.get("value", [])
        except Exception as e:
            logger.warning("Graph get_teams_channels failed: %s", e)
            return []

    async def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            params: dict = {"$top": "50"}
            data = await self._get(
                f"/teams/{team_id}/channels/{channel_id}/messages",
                params,
            )
            messages = data.get("value", [])
            if since:
                cutoff = since.isoformat()
                messages = [m for m in messages if m.get("createdDateTime", "") >= cutoff]
            return messages
        except Exception as e:
            logger.warning("Graph get_channel_messages failed: %s", e)
            return []

    async def get_meeting_transcript(self, online_meeting_id: str) -> Optional[str]:
        if not self.is_configured():
            return None
        try:
            path = f"/users/{self._user_email}/onlineMeetings/{online_meeting_id}/transcripts"
            data = await self._get(path)
            transcripts = data.get("value", [])
            if not transcripts:
                return None
            # Fetch the first transcript content
            transcript_id = transcripts[0]["id"]
            content_path = f"/users/{self._user_email}/onlineMeetings/{online_meeting_id}/transcripts/{transcript_id}/content"
            import aiohttp
            token = await self._get_token()
            headers = {"Authorization": f"Bearer {token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{GRAPH_BASE}{content_path}", headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.text()
            return None
        except Exception as e:
            logger.warning("Graph get_meeting_transcript failed: %s", e)
            return None

    async def get_joined_teams(self) -> list[dict]:
        if not self.is_configured():
            return []
        try:
            data = await self._get(f"/users/{self._user_email}/joinedTeams")
            return data.get("value", [])
        except Exception as e:
            logger.warning("Graph get_joined_teams failed: %s", e)
            return []

    # -- Helpers -----------------------------------------------------------

    def _msg_to_raw(self, msg: dict, folder: str) -> RawEmail:
        sender = ""
        try:
            sender = msg["from"]["emailAddress"]["address"]
        except (KeyError, TypeError):
            pass

        recipients: list[str] = []
        for field in ("toRecipients", "ccRecipients"):
            for r in msg.get(field, []):
                try:
                    recipients.append(r["emailAddress"]["address"])
                except (KeyError, TypeError):
                    pass

        body = ""
        try:
            body = msg["body"]["content"]
        except (KeyError, TypeError):
            pass

        received_at = datetime.now(timezone.utc)
        try:
            received_at = datetime.fromisoformat(
                msg["receivedDateTime"].replace("Z", "+00:00")
            )
        except Exception:
            pass

        return RawEmail(
            message_id=msg.get("id", ""),
            subject=msg.get("subject", "") or "",
            sender=sender,
            recipients=recipients,
            body=body,
            received_at=received_at,
            folder=folder,
            account=self._user_email,
            thread_id=msg.get("conversationId"),
            has_attachment=msg.get("hasAttachments", False),
            attachment_names=[],
        )

    def _event_to_raw(self, event: dict) -> RawCalendarItem:
        start_dt = datetime.now(timezone.utc)
        end_dt = datetime.now(timezone.utc)
        try:
            start_dt = datetime.fromisoformat(
                event["start"]["dateTime"].replace("Z", "+00:00")
            )
            end_dt = datetime.fromisoformat(
                event["end"]["dateTime"].replace("Z", "+00:00")
            )
        except Exception:
            pass

        attendees: list[MeetingAttendee] = []
        for a in event.get("attendees", []):
            try:
                status_map = {
                    "accepted": "accepted",
                    "declined": "declined",
                    "tentativelyAccepted": "tentative",
                    "none": "none",
                    "notResponded": "none",
                }
                attendees.append(MeetingAttendee(
                    name=a["emailAddress"]["name"],
                    email=a["emailAddress"]["address"],
                    response_status=status_map.get(a["status"]["response"], "none"),
                ))
            except (KeyError, TypeError):
                pass

        organizer = ""
        try:
            organizer = event["organizer"]["emailAddress"]["address"]
        except (KeyError, TypeError):
            pass

        body = ""
        try:
            body = event["body"]["content"]
        except (KeyError, TypeError):
            pass

        location = ""
        try:
            location = event["location"]["displayName"]
        except (KeyError, TypeError):
            pass

        is_teams = event.get("isOnlineMeeting", False)
        join_url: Optional[str] = None
        online_meeting_id: Optional[str] = None
        try:
            join_url = event["onlineMeeting"]["joinUrl"]
            online_meeting_id = event["onlineMeetingId"]
        except (KeyError, TypeError):
            pass

        my_response = "none"
        try:
            status_map = {
                "accepted": "accepted",
                "declined": "declined",
                "tentativelyAccepted": "tentative",
                "none": "none",
                "notResponded": "none",
                "organizer": "accepted",
            }
            my_response = status_map.get(event["responseStatus"]["response"], "none")
        except (KeyError, TypeError):
            pass

        return RawCalendarItem(
            subject=event.get("subject", "") or "",
            organizer=organizer,
            attendees=attendees,
            start_time=start_dt,
            end_time=end_dt,
            location=location,
            body=body,
            is_teams_meeting=is_teams,
            teams_join_url=join_url,
            online_meeting_id=online_meeting_id,
            my_response=my_response,
            global_id=event.get("id", ""),
        )
