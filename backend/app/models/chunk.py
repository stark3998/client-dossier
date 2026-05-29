# backend/app/models/chunk.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
import hashlib


class ChunkMetadata(BaseModel):
    file_path: str
    file_type: str
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    client_name: str
    last_modified: datetime


class Chunk(BaseModel):
    id: str = ""
    content: str
    chunk_hash: str = ""
    embedding: Optional[list[float]] = None
    metadata: ChunkMetadata

    def model_post_init(self, __context) -> None:
        if not self.chunk_hash:
            self.chunk_hash = hashlib.sha256(self.content.encode()).hexdigest()
        if not self.id:
            raw = f"{self.metadata.file_path}:{self.content}"
            self.id = hashlib.sha256(raw.encode()).hexdigest()
