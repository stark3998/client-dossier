# backend/app/ingestion/chunker.py
import hashlib
import logging
import re
from datetime import datetime, timezone

from app.models.chunk import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)
SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def chunk_document(
    sections: list,
    file_path: str,
    file_type: str,
    client_name: str,
    last_modified: datetime,
    max_tokens: int = 800,
    overlap_tokens: int = 100,
    doc_type: str | None = None,
    engagement_names: list[str] | None = None,
    key_topics: list[str] | None = None,
    document_date: str | None = None,
    deliverable_related: bool = False,
) -> list[Chunk]:
    from app.config import get_settings
    settings = get_settings()

    extra = dict(
        doc_type=doc_type,
        engagement_names=engagement_names or [],
        key_topics=key_topics or [],
        document_date=document_date,
        deliverable_related=deliverable_related,
    )

    # Use semantic chunking in production when embeddings are available
    if settings.SEMANTIC_CHUNKING and not settings.LOCAL_MODE:
        try:
            return _semantic_chunk_document(
                sections, file_path, file_type, client_name, last_modified, max_tokens, **extra
            )
        except Exception as e:
            logger.warning("Semantic chunking failed, falling back to token-based: %s", e)

    return _token_chunk_document(
        sections, file_path, file_type, client_name, last_modified, max_tokens, overlap_tokens, **extra
    )


def _semantic_chunk_document(
    sections: list,
    file_path: str,
    file_type: str,
    client_name: str,
    last_modified: datetime,
    max_tokens: int,
    doc_type: str | None = None,
    engagement_names: list[str] | None = None,
    key_topics: list[str] | None = None,
    document_date: str | None = None,
    deliverable_related: bool = False,
) -> list[Chunk]:
    from chonkie import SemanticChunker
    from app.services.embeddings import create_embedding_service
    import asyncio

    embedding_service = create_embedding_service()

    def _embed_fn(texts: list[str]) -> list[list[float]]:
        # Chonkie calls this synchronously; bridge to async embed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    fut = pool.submit(asyncio.run, embedding_service.embed_texts(texts))
                    return fut.result()
            else:
                return loop.run_until_complete(embedding_service.embed_texts(texts))
        except Exception:
            # If embedding bridge fails, raise so we fall back to token chunker
            raise

    chunker = SemanticChunker(
        embedding_function=_embed_fn,
        max_chunk_size=max_tokens,
        similarity_threshold=0.5,
    )

    chunks: list[Chunk] = []
    for section in sections:
        if not section.text.strip():
            continue
        try:
            raw_chunks = chunker.chunk(section.text)
            for rc in raw_chunks:
                text = rc.text if hasattr(rc, "text") else str(rc)
                chunks.append(_make_chunk(
                    content=text,
                    file_path=file_path,
                    file_type=file_type,
                    section_title=section.title,
                    page_number=section.page_number,
                    client_name=client_name,
                    last_modified=last_modified,
                    doc_type=doc_type,
                    engagement_names=engagement_names or [],
                    key_topics=key_topics or [],
                    document_date=document_date,
                    deliverable_related=deliverable_related,
                ))
        except Exception as e:
            logger.warning("Semantic chunking failed for section '%s': %s", section.title, e)
            # Fall back to single chunk for this section
            chunks.append(_make_chunk(
                content=section.text,
                file_path=file_path,
                file_type=file_type,
                section_title=section.title,
                page_number=section.page_number,
                client_name=client_name,
                last_modified=last_modified,
                doc_type=doc_type,
                engagement_names=engagement_names or [],
                key_topics=key_topics or [],
                document_date=document_date,
                deliverable_related=deliverable_related,
            ))
    return chunks


def _token_chunk_document(
    sections: list,
    file_path: str,
    file_type: str,
    client_name: str,
    last_modified: datetime,
    max_tokens: int,
    overlap_tokens: int,
    doc_type: str | None = None,
    engagement_names: list[str] | None = None,
    key_topics: list[str] | None = None,
    document_date: str | None = None,
    deliverable_related: bool = False,
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
                doc_type=doc_type,
                engagement_names=engagement_names or [],
                key_topics=key_topics or [],
                document_date=document_date,
                deliverable_related=deliverable_related,
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
                        doc_type=doc_type,
                        engagement_names=engagement_names or [],
                        key_topics=key_topics or [],
                        document_date=document_date,
                        deliverable_related=deliverable_related,
                    ))
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
                    doc_type=doc_type,
                    engagement_names=engagement_names or [],
                    key_topics=key_topics or [],
                    document_date=document_date,
                    deliverable_related=deliverable_related,
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
    doc_type: str | None = None,
    engagement_names: list[str] | None = None,
    key_topics: list[str] | None = None,
    document_date: str | None = None,
    deliverable_related: bool = False,
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
            doc_type=doc_type,
            engagement_names=engagement_names or [],
            key_topics=key_topics or [],
            document_date=document_date,
            deliverable_related=deliverable_related,
        ),
    )
