# backend/app/services/embeddings.py
import hashlib
import logging
import random
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Azure OpenAI embedding service."""

    def __init__(self):
        self._client = None

    async def initialize(self):
        settings = get_settings()
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )
        logger.info("Embedding service initialized")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        settings = get_settings()
        all_embeddings = []
        batch_size = 16
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = await self._client.embeddings.create(
                input=batch,
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
                dimensions=3072,
            )
            all_embeddings.extend([item.embedding for item in response.data])
        return all_embeddings

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0]

    async def close(self):
        if self._client:
            await self._client.close()


class LocalEmbeddingService:
    """Deterministic random vectors for LOCAL_MODE."""

    async def initialize(self):
        logger.info("Local embedding service initialized")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._deterministic_vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._deterministic_vector(text)

    def _deterministic_vector(self, text: str) -> list[float]:
        seed = int(hashlib.sha256(text.encode()).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        vec = [rng.gauss(0, 1) for _ in range(3072)]
        norm = sum(x * x for x in vec) ** 0.5
        return [x / norm for x in vec]

    async def close(self):
        pass


def create_embedding_service() -> EmbeddingService | LocalEmbeddingService:
    settings = get_settings()
    if settings.LOCAL_MODE:
        return LocalEmbeddingService()
    return EmbeddingService()
