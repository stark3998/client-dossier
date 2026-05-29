# backend/app/models/custom_tool.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[str] = None


class CustomTool(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    prompt_template: str
    parameters: list[ToolParameter] = []
    category: str = "custom"
    icon: str = "tool"
    created_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
