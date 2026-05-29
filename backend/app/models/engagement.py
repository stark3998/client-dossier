# backend/app/models/engagement.py
import uuid
from datetime import datetime, timezone
from typing import Optional, Literal
from pydantic import BaseModel, Field


class Engagement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_name: str
    phase: Literal["discovery", "design", "execute", "deliver", "sustain"] = "discovery"
    status: Literal["active", "completed", "on-hold", "cancelled"] = "active"
    description: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    budget: Optional[float] = None
    team: list[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusUpdate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    engagement_id: str
    date: str
    author: str = ""
    summary: str
    sentiment: Literal["positive", "neutral", "negative", "concerning"] = "neutral"
    source_file: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Deliverable(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    type: Literal["document", "presentation", "report", "code", "other"] = "document"
    engagement_id: str
    status: Literal["draft", "review", "delivered", "accepted"] = "draft"
    due_date: Optional[str] = None
    owner: str = ""
    feedback: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Risk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    probability: int = 3
    impact: int = 3
    mitigation: str = ""
    status: Literal["open", "mitigating", "resolved", "accepted"] = "open"
    engagement_id: str
    owner: str = ""
    category: Literal["technical", "commercial", "operational", "timeline"] = "operational"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Interaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: Literal["meeting", "call", "email", "workshop"] = "meeting"
    date: str
    participants: list[str] = []
    summary: str = ""
    action_items: list[str] = []
    source_file: Optional[str] = None
    engagement_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
