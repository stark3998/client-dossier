# backend/app/models/analysis.py
import uuid
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ExtractedStakeholder(BaseModel):
    name: str
    title: Optional[str] = None
    email: Optional[str] = None
    organization: Optional[str] = None
    confidence: float = 0.0


class ExtractedActionItem(BaseModel):
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    source_section: Optional[str] = None


class ExtractedRisk(BaseModel):
    description: str
    severity: Optional[str] = None
    category: Optional[str] = None
    source_section: Optional[str] = None


class ExtractedDate(BaseModel):
    date: str
    description: str
    date_type: str = ""


class AnalysisResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    client_name: str
    doc_type: str = "unknown"
    extracted_stakeholders: list[ExtractedStakeholder] = []
    extracted_actions: list[ExtractedActionItem] = []
    extracted_dates: list[ExtractedDate] = []
    extracted_risks: list[ExtractedRisk] = []
    engagement_references: list[str] = []
    key_topics: list[str] = []
    analysis_summary: str = ""
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
