# backend/app/models/client_memory.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Stakeholder(BaseModel):
    name: str
    title: Optional[str] = None
    email: Optional[str] = None


class Deliverable(BaseModel):
    title: str
    date: Optional[datetime] = None
    file_path: Optional[str] = None


class ActionItem(BaseModel):
    description: str
    owner: Optional[str] = None
    due_date: Optional[datetime] = None
    completed: bool = False


class ClientMemory(BaseModel):
    id: str = ""
    client_name: str
    industry: Optional[str] = None
    key_stakeholders: list[Stakeholder] = []
    active_engagements: list[str] = []
    financials_summary: Optional[str] = None
    pain_points: list[str] = []
    strategic_priorities: list[str] = []
    past_deliverables: list[Deliverable] = []
    open_action_items: list[ActionItem] = []
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    sources: list[str] = []

    def model_post_init(self, __context) -> None:
        if not self.id:
            self.id = self.client_name.lower().replace(" ", "-")
