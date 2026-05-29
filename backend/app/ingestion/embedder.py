# backend/app/ingestion/embedder.py
import logging

from app.models.chunk import Chunk

logger = logging.getLogger(__name__)


async def embed_chunks(chunks: list[Chunk], embedding_service) -> list[Chunk]:
    if not chunks:
        return chunks

    texts = [c.content for c in chunks]
    logger.info("Embedding %d chunks", len(texts))

    embeddings = await embedding_service.embed_texts(texts)

    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding

    return chunks
