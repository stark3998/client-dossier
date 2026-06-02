# backend/app/models/communication.py
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class OutlookAccount(BaseModel):
    display_name: str
    folders: list[str] = ["Inbox", "Sent Items"]


class CommunicationConfig(BaseModel):
    id: str                          # = client_id
    client_name: str
    domains: list[str] = []          # e.g. ["@acme.com"]
    keywords: list[str] = []         # subject/body match terms
    accounts: list[OutlookAccount] = []
    contacts: list[str] = []         # specific email addresses
    scan_sent: bool = True
    auto_draft: bool = True
    scan_interval_minutes: int = 15
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScannedEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    message_id: str = ""
    subject: str = ""
    sender: str = ""
    recipients: list[str] = []
    body_preview: str = ""
    body_full: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    folder: str = "Inbox"
    account: str = ""
    thread_id: Optional[str] = None
    has_draft_reply: bool = False
    draft_reply_id: Optional[str] = None
    attribution_reason: str = "domain_match"   # "domain_match" | "keyword_match" | "contact_match"
    has_attachment: bool = False
    attachment_names: list[str] = []
    indexed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingAttendee(BaseModel):
    name: str = ""
    email: str = ""
    response_status: str = "none"    # "accepted" | "declined" | "tentative" | "none"


class MeetingLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    subject: str = ""
    organizer: str = ""
    attendees: list[MeetingAttendee] = []
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: str = ""
    agenda: str = ""
    is_teams_meeting: bool = False
    teams_join_url: Optional[str] = None
    online_meeting_id: Optional[str] = None
    my_response: str = "none"        # "accepted" | "declined" | "tentative" | "none"
    transcript_summary: Optional[str] = None
    action_items_extracted: list[str] = []
    indexed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DraftReply(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    email_id: str
    subject: str = ""
    to: list[str] = []
    cc: list[str] = []
    body: str = ""
    status: str = "pending_review"   # "pending_review" | "edited" | "pushed_to_outlook" | "discarded"
    feedback: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    pushed_at: Optional[datetime] = None
    outlook_entry_id: Optional[str] = None


# Raw intermediary types used by service layer before model mapping

class RawEmail(BaseModel):
    message_id: str = ""
    subject: str = ""
    sender: str = ""
    recipients: list[str] = []
    body: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    folder: str = "Inbox"
    account: str = ""
    thread_id: Optional[str] = None
    has_attachment: bool = False
    attachment_names: list[str] = []


class RawCalendarItem(BaseModel):
    subject: str = ""
    organizer: str = ""
    attendees: list[MeetingAttendee] = []
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: str = ""
    body: str = ""
    is_teams_meeting: bool = False
    teams_join_url: Optional[str] = None
    online_meeting_id: Optional[str] = None
    my_response: str = "none"
    global_id: str = ""
