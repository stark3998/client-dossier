# backend/app/models/mcp_server.py
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    endpoint: str
    description: str = ""
    auth_type: str = "none"
    auth_config: dict = {}
    capabilities: list[str] = []
    protocol: str = "rest"  # "rest" (custom HTTP) or "sse" (standard MCP over SSE)
    enabled: bool = True
    status: str = "unknown"
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
