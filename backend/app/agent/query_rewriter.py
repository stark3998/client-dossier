import asyncio
import json
import logging
from typing import Optional

from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

_HYDE_PROMPT = (
    "Write a 3-sentence excerpt from a professional consulting document that would directly answer "
    "the following question. Use formal language and domain-specific terminology. "
    "Output only the excerpt, no preamble.\n\nQuestion: "
)


class QueryRewriter:
    def __init__(self, kernel, embedding_service=None):
        self._kernel = kernel
        self._embeddings = embedding_service

    async def rewrite(self, query: str) -> list[str]:
        """Generate 2-3 search query variants from the user's question."""
        try:
            from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
            from semantic_kernel.contents import ChatHistory
            from app.agent.kernel import get_execution_settings

            chat_service = self._kernel.get_service(type=ChatCompletionClientBase)
            history = ChatHistory()
            history.add_user_message(load_prompt("query_rewrite_prompt.txt") + query)

            settings = get_execution_settings(auto_invoke=True)
            settings.max_tokens = 256
            settings.temperature = 0.3

            result_text = ""
            response = chat_service.get_streaming_chat_message_content(
                chat_history=history,
                settings=settings,
                kernel=self._kernel,
            )
            async for chunk in response:
                result_text += str(chunk)

            queries = json.loads(result_text)
            if isinstance(queries, list):
                return [query] + queries[:2]
        except Exception as e:
            logger.warning("Query rewriting failed: %s", e)

        return [query]

    async def search_with_rewriting(
        self, query: str, search_fn, client_name: str = "", top: int = 8
    ) -> list[dict]:
        """Rewrite query, run parallel searches, merge and deduplicate results."""
        queries = await self.rewrite(query)

        results = await asyncio.gather(*[
            search_fn(q, client_name, top) for q in queries
        ])

        seen_ids: set[str] = set()
        merged: list[dict] = []
        for result_set in results:
            if isinstance(result_set, str):
                try:
                    result_set = json.loads(result_set)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(result_set, list):
                for item in result_set:
                    item_id = item.get("id") or item.get("file_path", "")
                    if item_id and item_id not in seen_ids:
                        seen_ids.add(item_id)
                        merged.append(item)

        merged.sort(key=lambda x: x.get("score", 0), reverse=True)
        return merged[:top]

    async def generate_hyde_embedding(self, query: str) -> list[float] | None:
        """Generate a hypothetical document embedding for the query (HyDE)."""
        if not self._embeddings:
            return None
        try:
            from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
            from semantic_kernel.contents import ChatHistory
            from app.agent.kernel import get_execution_settings

            chat_service = self._kernel.get_service(type=ChatCompletionClientBase)
            history = ChatHistory()
            history.add_user_message(_HYDE_PROMPT + query)

            settings = get_execution_settings(auto_invoke=False)
            settings.max_tokens = 200
            settings.temperature = 0.5

            hypothetical = ""
            async for chunk in chat_service.get_streaming_chat_message_content(
                chat_history=history, settings=settings, kernel=self._kernel
            ):
                hypothetical += str(chunk)

            if hypothetical.strip():
                return await self._embeddings.embed_query(hypothetical.strip())
        except Exception as e:
            logger.warning("HyDE generation failed: %s", e)
        return None
