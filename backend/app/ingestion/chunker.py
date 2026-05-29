# backend/app/ingestion/chunker.py
import hashlib
import re
from datetime import datetime, timezone

from app.models.chunk import Chunk, ChunkMetadata

SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def chunk_document(
    sections: list,
    file_path: str,
    file_type: str,
    client_name: str,
    last_modified: datetime,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    chunks = []

    for section in sections:
        section_tokens = enc.encode(section.text)

        if len(section_tokens) <= max_tokens:
            chunks.append(_make_chunk(
                content=section.text,
                file_path=file_path,
                file_type=file_type,
                section_title=section.title,
                page_number=section.page_number,
                client_name=client_name,
                last_modified=last_modified,
            ))
        else:
            sentences = SENTENCE_PATTERN.split(section.text)
            current_tokens = []
            current_text_parts = []

            for sentence in sentences:
                sent_tokens = enc.encode(sentence)

                if len(current_tokens) + len(sent_tokens) > max_tokens and current_text_parts:
                    text = " ".join(current_text_parts)
                    chunks.append(_make_chunk(
                        content=text,
                        file_path=file_path,
                        file_type=file_type,
                        section_title=section.title,
                        page_number=section.page_number,
                        client_name=client_name,
                        last_modified=last_modified,
                    ))
                    # Overlap: keep last N tokens worth of text
                    overlap_text_parts = []
                    overlap_count = 0
                    for part in reversed(current_text_parts):
                        part_len = len(enc.encode(part))
                        if overlap_count + part_len > overlap_tokens:
                            break
                        overlap_text_parts.insert(0, part)
                        overlap_count += part_len
                    current_text_parts = overlap_text_parts
                    current_tokens = enc.encode(" ".join(current_text_parts)) if current_text_parts else []

                current_text_parts.append(sentence)
                current_tokens = enc.encode(" ".join(current_text_parts))

            if current_text_parts:
                text = " ".join(current_text_parts)
                chunks.append(_make_chunk(
                    content=text,
                    file_path=file_path,
                    file_type=file_type,
                    section_title=section.title,
                    page_number=section.page_number,
                    client_name=client_name,
                    last_modified=last_modified,
                ))

    return chunks


def _make_chunk(
    content: str,
    file_path: str,
    file_type: str,
    section_title: str | None,
    page_number: int | None,
    client_name: str,
    last_modified: datetime,
) -> Chunk:
    return Chunk(
        content=content,
        metadata=ChunkMetadata(
            file_path=file_path,
            file_type=file_type,
            section_title=section_title,
            page_number=page_number,
            client_name=client_name,
            last_modified=last_modified,
        ),
    )
