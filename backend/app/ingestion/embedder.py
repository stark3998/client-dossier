# backend/app/ingestion/embedder.py
import asyncio
import logging

from app.models.chunk import Chunk

logger = logging.getLogger(__name__)

_RETRY_DELAYS = (1, 2, 4, 8)


async def embed_chunks(chunks: list[Chunk], embedding_service) -> list[Chunk]:
    if not chunks:
        return chunks

    texts = [c.content for c in chunks]
    logger.info("Embedding %d chunks", len(texts))

    embeddings = await _embed_with_retry(embedding_service, texts)

    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    return chunks


async def _embed_with_retry(embedding_service, texts: list[str]) -> list:
    last_exc: Exception = RuntimeError("embedding not attempted")
    for attempt, delay in enumerate((0, *_RETRY_DELAYS)):
        if delay:
            logger.warning(
                "Embedding rate limited, retrying in %ds (attempt %d/%d)",
                delay, attempt, len(_RETRY_DELAYS) + 1,
            )
            await asyncio.sleep(delay)
        try:
            return await embedding_service.embed_texts(texts)
        except Exception as exc:
            if not _is_rate_limit(exc):
                raise
            last_exc = exc
    raise last_exc


def _is_rate_limit(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg
