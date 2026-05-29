# app/agent/search_plugin.py
import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class SearchPlugin:
    def __init__(self, search_service, embedding_service):
        self._search = search_service
        self._embeddings = embedding_service

    @kernel_function(
        name="search_documents",
        description="Search client documents using natural language. Returns relevant document chunks with source file paths, section titles, and page numbers."
    )
    async def search_documents(self, query: str, client_name: str = "", top: int = 8) -> str:
        vector = await self._embeddings.embed_query(query)
        filters = f"client_name eq '{client_name}'" if client_name else None
        results = await self._search.hybrid_search(
            query_text=query, query_vector=vector, top=top, filters=filters
        )
        formatted = []
        for r in results:
            formatted.append({
                "content": r["content"][:500],
                "file_path": r["file_path"],
                "section_title": r.get("section_title", ""),
                "page_number": r.get("page_number"),
                "score": r.get("score", 0),
            })
        return json.dumps(formatted, indent=2)
