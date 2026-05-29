# backend/app/models/message.py
from datetime import datetime
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field
import uuid


class SourceChip(BaseModel):
    file_path: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    excerpt: str = ""
    score: float = 0.0


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: Literal["user", "assistant", "system"]
    content: str
    sources: list[SourceChip] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    type: str = "message"
    content: str
    client_name: Optional[str] = None
    session_id: Optional[str] = None


class StreamEvent(BaseModel):
    type: Literal[
        "token", "source", "done", "error",
        "thought", "plan", "plan_step", "tool_call", "tool_result",
    ]
    content: Optional[str] = None
    source: Optional[SourceChip] = None
    message: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[dict] = None
    step_number: Optional[int] = None
    step_total: Optional[int] = None
    plan_steps: Optional[list[str]] = None
