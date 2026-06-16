# backend/app/agent/email_query_analyzer.py
"""
Analyzes a natural language email search query via the LLM and returns
expanded query variants plus structured filters (sender, date range, folder, etc.).
"""
import json
import logging
from datetime import datetime, timezone

from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

_PROMPT: str | None = None


def _get_prompt() -> str:
    global _PROMPT
    if _PROMPT is None:
        _PROMPT = load_prompt("email_search_analyze_prompt.txt")
    return _PROMPT


class EmailQueryAnalyzer:
    """Uses the configured LLM kernel to decompose a search query into
    expanded text variants and extractable filters."""

    def __init__(self, kernel) -> None:
        self._kernel = kernel

    async def analyze(self, query: str, conversation_history: list[dict]) -> dict:
        """Return a dict with ``expanded_queries`` (list[str]) and ``filters`` (dict).

        Falls back gracefully to ``{"expanded_queries": [query], "filters": {...nulls}}``
        if the LLM call fails or the kernel has no chat service.
        """
        today = datetime.now(timezone.utc).date().isoformat()
        system = _get_prompt()

        messages: list[dict] = []
        for msg in conversation_history[-6:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": f"Today is {today}. Query: {query}"})

        try:
            from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
            from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
            from semantic_kernel.contents import ChatHistory

            chat_service = self._kernel.get_service(type=ChatCompletionClientBase)

            chat = ChatHistory(system_message=system)
            for m in messages[:-1]:
                if m["role"] == "user":
                    chat.add_user_message(m["content"])
                else:
                    chat.add_assistant_message(m["content"])
            chat.add_user_message(messages[-1]["content"])

            settings = AzureChatPromptExecutionSettings(
                service_id="chat",
                max_tokens=512,
                temperature=0,
            )
            response = await chat_service.get_chat_message_content(chat, settings=settings)
            raw = str(response).strip()

            # Strip markdown fences if the model wraps its output
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            data: dict = json.loads(raw)
            return data

        except Exception as e:
            logger.warning("Email query analysis failed: %s", e)
            return {
                "expanded_queries": [query],
                "filters": {
                    "sender_name": None,
                    "sender_domain": None,
                    "date_from": None,
                    "date_to": None,
                    "folder": None,
                    "has_attachment": None,
                },
            }
