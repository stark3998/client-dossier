# backend/app/services/search.py
import logging
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

try:
    from flashrank import Ranker, RerankRequest as FlashRerankRequest
    _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
    _flashrank_available = True
except Exception:
    _ranker = None
    _flashrank_available = False


class SearchService:
    """Azure AI Search wrapper for hybrid vector + BM25 search."""

    def __init__(self):
        self._index_client = None
        self._search_client = None

    async def initialize(self):
        settings = get_settings()
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient
        from azure.core.credentials import AzureKeyCredential

        credential = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
        self._index_client = SearchIndexClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT, credential=credential
        )
        self._search_client = SearchClient(
            endpoint=settings.AZURE_SEARCH_ENDPOINT,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            credential=credential,
        )
        logger.info("Azure AI Search initialized")

    async def ensure_index(self):
        from azure.search.documents.indexes.models import (
            SearchIndex,
            SearchField,
            SearchFieldDataType,
            SimpleField,
            SearchableField,
            VectorSearch,
            HnswAlgorithmConfiguration,
            VectorSearchProfile,
            SemanticConfiguration,
            SemanticSearch,
            SemanticPrioritizedFields,
            SemanticField,
        )

        settings = get_settings()
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=3072,
                vector_search_profile_name="hnsw-profile",
            ),
            SimpleField(name="file_path", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="section_title", type=SearchFieldDataType.String),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32),
            SimpleField(name="client_name", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="chunk_hash", type=SearchFieldDataType.String),
            SimpleField(name="last_modified", type=SearchFieldDataType.DateTimeOffset, sortable=True),
        ]

        vector_search = VectorSearch(
            profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-config")],
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
        )

        semantic_config = SemanticConfiguration(
            name="semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")],
                title_field=SemanticField(field_name="section_title"),
            ),
        )

        index = SearchIndex(
            name=settings.AZURE_SEARCH_INDEX_NAME,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
        )

        self._index_client.create_or_update_index(index)
        logger.info("Search index ensured: %s", settings.AZURE_SEARCH_INDEX_NAME)

    async def hybrid_search(
        self, query_text: str, query_vector: list[float], top: int = 8, filters: str | None = None
    ) -> list[dict]:
        from azure.search.documents.models import VectorizedQuery

        vector_query = VectorizedQuery(
            vector=query_vector, k_nearest_neighbors=top, fields="content_vector"
        )
        kwargs: dict[str, Any] = {
            "search_text": query_text,
            "vector_queries": [vector_query],
            "top": top,
            "select": ["id", "content", "file_path", "file_type", "section_title", "page_number", "client_name"],
        }
        if filters:
            kwargs["filter"] = filters

        results = []
        for result in self._search_client.search(**kwargs):
            results.append({
                "id": result["id"],
                "content": result["content"],
                "file_path": result["file_path"],
                "file_type": result.get("file_type", ""),
                "section_title": result.get("section_title", ""),
                "page_number": result.get("page_number"),
                "client_name": result.get("client_name", ""),
                "score": result.get("@search.score", 0.0),
            })
        return results

    def rerank(self, query: str, results: list[dict], top_k: int = 8) -> list[dict]:
        settings = get_settings()
        if not settings.RERANK_ENABLED or not _flashrank_available or not results:
            return results[:top_k]
        try:
            passages = [{"id": i, "text": r.get("content", "")} for i, r in enumerate(results)]
            request = FlashRerankRequest(query=query, passages=passages)
            reranked = _ranker.rerank(request)
            ordered = sorted(reranked, key=lambda x: x.get("score", 0), reverse=True)
            return [results[item["id"]] for item in ordered[:top_k]]
        except Exception as e:
            logger.warning("Reranking failed, using original order: %s", e)
            return results[:top_k]

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        self._search_client.upload_documents(documents=chunks)

    async def delete_by_source(self, file_path: str) -> None:
        results = self._search_client.search(
            search_text="*", filter=f"file_path eq '{file_path}'", select=["id"]
        )
        ids = [{"id": r["id"]} for r in results]
        if ids:
            self._search_client.delete_documents(documents=ids)

    async def close(self):
        if self._search_client:
            self._search_client.close()
        if self._index_client:
            self._index_client.close()


class LocalSearchService:
    """In-memory search stub for LOCAL_MODE."""

    def __init__(self):
        self._documents: dict[str, dict] = {}

    async def initialize(self):
        logger.info("Local search service initialized")

    async def ensure_index(self):
        pass

    async def hybrid_search(
        self, query_text: str, query_vector: list[float], top: int = 8, filters: str | None = None
    ) -> list[dict]:
        query_lower = query_text.lower()
        scored = []
        for doc in self._documents.values():
            content_lower = doc.get("content", "").lower()
            words = query_lower.split()
            matches = sum(1 for w in words if w in content_lower)
            if matches > 0:
                score = matches / max(len(words), 1)
                scored.append({**doc, "score": score})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top]

    def rerank(self, query: str, results: list[dict], top_k: int = 8) -> list[dict]:
        return results[:top_k]

    async def upsert_chunks(self, chunks: list[dict]) -> None:
        for chunk in chunks:
            self._documents[chunk["id"]] = chunk

    async def delete_by_source(self, file_path: str) -> None:
        to_delete = [k for k, v in self._documents.items() if v.get("file_path") == file_path]
        for k in to_delete:
            del self._documents[k]

    async def close(self):
        pass


def create_search_service() -> SearchService | LocalSearchService:
    settings = get_settings()
    if settings.LOCAL_MODE:
        return LocalSearchService()
    return SearchService()
