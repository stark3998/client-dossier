from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Alert(BaseModel):
    type: Literal["overdue_action", "high_risk", "stale_engagement", "new_analysis"]
    severity: Literal["info", "warning", "critical"]
    title: str
    detail: str
    client_name: str = ""
    entity_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
