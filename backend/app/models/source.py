# backend/app/models/source.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


@dataclass
class DocumentSection:
    title: Optional[str]
    text: str
    page_number: Optional[int] = None


@dataclass
class ParsedDocument:
    file_path: str
    file_type: str
    last_modified: datetime
    sections: list[DocumentSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SourceDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    file_path: str
    file_type: str
    chunk_count: int = 0
    content_hash: str = ""
    last_indexed: datetime = Field(default_factory=datetime.utcnow)


class IngestJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    mode: str = "incremental"
    path: str = ""
    client_name: str = ""
    total_files: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    active_files: list[str] = Field(default_factory=list)
    file_events: list[dict] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    @property
    def progress(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.processed_files / self.total_files
