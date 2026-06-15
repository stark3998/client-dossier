# app/agent/search_plugin.py
import json
import logging
from datetime import datetime, timezone
from semantic_kernel.functions import kernel_function
from app.config import get_settings

logger = logging.getLogger(__name__)


def _apply_recency_boost(results: list[dict]) -> list[dict]:
    """Boost score linearly by document recency — max +0.15 for brand-new content, 0 at 365 days."""
    now = datetime.now(timezone.utc)
    for r in results:
        raw_date = r.get("last_modified") or r.get("document_date") or ""
        try:
            dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            age_days = max((now - dt).days, 0)
            decay = max(0.0, 1.0 - age_days / 365)
            r["score"] = r.get("score", 0.0) + 0.15 * decay
        except (ValueError, TypeError, AttributeError):
            pass
    return results


class SearchPlugin:
    def __init__(self, search_service, embedding_service):
        self._search = search_service
        self._embeddings = embedding_service
        # Lazy-initialised once kernel is available
        self._rewriter = None

    def set_rewriter(self, rewriter) -> None:
        self._rewriter = rewriter

    @kernel_function(
        name="search_documents",
        description="Search client documents using natural language. Returns relevant document chunks with source file paths, section titles, and page numbers."
    )
    async def search_documents(self, query: str, client_name: str = "", top: int = 8) -> str:
        vector = await self._embeddings.embed_query(query)
        filters = f"client_name eq '{client_name}'" if client_name else None
        # Fetch wider candidate set for reranking
        candidates = await self._search.hybrid_search(
            query_text=query, query_vector=vector, top=max(top * 3, 20), filters=filters
        )
        results = self._search.rerank(query, candidates, top_k=top)
        results = _apply_recency_boost(results)
        min_score = get_settings().SEARCH_MIN_SCORE
        results = [r for r in results if r.get("score", 0) >= min_score]
        formatted = []
        for r in results:
            formatted.append({
                "content": r["content"][:500],
                "file_path": r["file_path"],
                "section_title": r.get("section_title", ""),
                "page_number": r.get("page_number"),
                "score": round(r.get("score", 0), 4),
            })
        return json.dumps(formatted, indent=2)

    @kernel_function(
        name="search_with_rewriting",
        description="Enhanced document search: rewrites the query into multiple variants and uses HyDE (hypothetical document embeddings) for better recall. Use for complex or ambiguous questions."
    )
    async def search_with_rewriting(self, query: str, client_name: str = "", top: int = 8) -> str:
        import asyncio

        filters = f"client_name eq '{client_name}'" if client_name else None

        # 1. Standard query embedding
        async def _search_with_vector(q: str, vector: list[float]) -> list[dict]:
            return await self._search.hybrid_search(
                query_text=q, query_vector=vector, top=max(top * 3, 20), filters=filters
            )

        tasks = []
        query_vector = await self._embeddings.embed_query(query)
        tasks.append(_search_with_vector(query, query_vector))

        # 2. Rewritten query variants
        if self._rewriter:
            rewrites = await self._rewriter.rewrite(query)
            for alt in rewrites[1:]:  # skip first (original)
                alt_vec = await self._embeddings.embed_query(alt)
                tasks.append(_search_with_vector(alt, alt_vec))

            # 3. HyDE pass
            hyde_vector = await self._rewriter.generate_hyde_embedding(query)
            if hyde_vector:
                tasks.append(_search_with_vector(query, hyde_vector))

        all_results = await asyncio.gather(*tasks)

        seen_ids: set[str] = set()
        merged: list[dict] = []
        for result_set in all_results:
            for r in result_set:
                rid = r.get("id") or r.get("file_path", "")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    merged.append(r)

        # Rerank the merged candidate pool
        reranked = self._search.rerank(query, merged, top_k=top)
        reranked = _apply_recency_boost(reranked)
        min_score = get_settings().SEARCH_MIN_SCORE
        reranked = [r for r in reranked if r.get("score", 0) >= min_score]

        formatted = [{
            "content": r["content"][:500],
            "file_path": r["file_path"],
            "section_title": r.get("section_title", ""),
            "page_number": r.get("page_number"),
            "score": round(r.get("score", 0), 4),
        } for r in reranked]
        return json.dumps(formatted, indent=2)
