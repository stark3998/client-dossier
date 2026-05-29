# app/agent/planner.py
import json
import logging
from typing import AsyncGenerator

from app.config import get_settings
from app.models.message import StreamEvent, SourceChip
from app.telemetry import track_event

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a Client Intelligence Agent — a senior consulting advisor that maintains comprehensive intelligence about clients. You help consulting professionals prepare for meetings, track engagements, manage deliverables, assess risks, and generate documents.

Available tools:

DOCUMENT SEARCH & FILES:
- search_documents: Search indexed client documents using natural language
- list_files: Browse available client documents
- read_file_preview: Preview document contents

CLIENT MEMORY:
- recall_client_memory: Retrieve stored client information (stakeholders, engagements, pain points, etc.)
- update_client_memory: Store new client facts learned during conversations

ENGAGEMENT MANAGEMENT:
- recall_engagements: List all projects/engagements with phase, status, team
- create_engagement: Create a new engagement/project
- recall_risks: List risks, optionally filtered by engagement
- recall_recent_interactions: View recent meetings, calls, emails
- log_interaction: Record a new client interaction

DOCUMENT GENERATION:
- generate_presentation: Create PowerPoint presentations
- generate_document: Create Word documents

EXTERNAL SOURCES (if configured):
- search_ms_learn: Search Microsoft Learn for technical guidance
- search_ms_graph: Search Microsoft Graph for emails/calendar

Guidelines:
- Always cite sources with file paths and page/section references when using document search
- Proactively update client memory when you learn new facts
- When preparing for meetings, pull from engagements, recent interactions, and open action items
- Track engagement phases (discovery -> design -> execute -> deliver -> sustain)
- Flag risks when you identify concerns in documents or conversations
- Log interactions when the user describes meetings or calls
- Be concise but thorough — a senior consultant's brief, not a research paper
"""


class AgentPlanner:
    def __init__(self, kernel, plugins: dict):
        self._kernel = kernel
        for name, plugin in plugins.items():
            kernel.add_plugin(plugin, plugin_name=name)
        logger.info("Agent planner initialized with plugins: %s", list(plugins.keys()))

    async def stream_response(
        self, chat_history, user_message: str, client_name: str | None = None
    ) -> AsyncGenerator[StreamEvent, None]:
        import time
        start = time.time()

        chat_history.add_user_message(user_message)

        settings = get_settings()
        if settings.LOCAL_MODE and not settings.AZURE_OPENAI_ENDPOINT:
            yield StreamEvent(type="token", content="[LOCAL_MODE] Agent responses require an Azure OpenAI endpoint. Configure AZURE_OPENAI_ENDPOINT to enable chat.")
            yield StreamEvent(type="done")
            return

        track_event("agent.chat.request", {
            "client_name": client_name or "unknown",
            "query_length": len(user_message),
        })

        try:
            from app.agent.kernel import get_execution_settings
            from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

            execution_settings = get_execution_settings()
            chat_service = self._kernel.get_service(type=ChatCompletionClientBase)

            source_count = 0
            token_count = 0
            full_content = []

            response = chat_service.get_streaming_chat_message_content(
                chat_history=chat_history,
                settings=execution_settings,
                kernel=self._kernel,
            )

            async for chunk in response:
                text = str(chunk)
                if text:
                    full_content.append(text)
                    token_count += 1
                    yield StreamEvent(type="token", content=text)

                # Check for function results that contain source info
                if hasattr(chunk, "items"):
                    for item in chunk.items:
                        if hasattr(item, "result") and item.result:
                            sources = _extract_sources(item.result)
                            for source in sources:
                                source_count += 1
                                yield StreamEvent(type="source", source=source)

            full_response = "".join(full_content)
            chat_history.add_assistant_message(full_response)

            duration_ms = int((time.time() - start) * 1000)
            track_event("agent.chat.response", {
                "client_name": client_name or "unknown",
                "source_count": source_count,
                "token_count": token_count,
                "duration_ms": duration_ms,
            })

            yield StreamEvent(type="done")

        except Exception as e:
            logger.error("Agent error: %s", e)
            yield StreamEvent(type="error", message=str(e))


def _extract_sources(result: str) -> list[SourceChip]:
    try:
        data = json.loads(result)
        if isinstance(data, list):
            sources = []
            for item in data:
                if "file_path" in item:
                    sources.append(SourceChip(
                        file_path=item["file_path"],
                        section_title=item.get("section_title"),
                        page_number=item.get("page_number"),
                        excerpt=item.get("content", "")[:200],
                        score=item.get("score", 0),
                    ))
            return sources
    except (json.JSONDecodeError, TypeError):
        pass
    return []
