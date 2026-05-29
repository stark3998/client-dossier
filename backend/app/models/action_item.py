from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field
import uuid


class ActionItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    owner: str = ""
    due_date: Optional[str] = None
    engagement_id: str = ""
    status: Literal["open", "in_progress", "completed", "cancelled"] = "open"
    priority: Literal["high", "medium", "low"] = "medium"
    source_file: Optional[str] = None
    source_analysis_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
