# app/agent/planner.py
import json
import logging
from typing import AsyncGenerator

from app.config import get_settings
from app.models.message import StreamEvent, SourceChip
from app.prompts.loader import load_prompt
from app.telemetry import track_event

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = load_prompt("system_prompt.txt")


class AgentPlanner:
    def __init__(self, kernel, plugins: dict, cosmos_manager=None):
        self._kernel = kernel
        self._cosmos_manager = cosmos_manager
        for name, plugin in plugins.items():
            kernel.add_plugin(plugin, plugin_name=name)

        from app.agent.context_injector import ContextInjector
        from app.agent.conversation_manager import ConversationManager
        self._context_injector = ContextInjector(cosmos_manager)
        self._conversation_manager = ConversationManager(kernel)

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
            # Conversation management: summarize if history is too long
            await self._conversation_manager.maybe_summarize(chat_history)

            # Auto-context injection
            if client_name:
                context_block = await self._context_injector.build_context_block(client_name)
                if context_block:
                    chat_history.add_system_message(context_block)

            from app.agent.kernel import get_execution_settings
            from app.agent.react_loop import run_react_loop
            from app.agent.planner_executor import is_complex_query, plan_and_execute

            execution_settings = get_execution_settings(auto_invoke=False)

            source_count = 0
            token_count = 0

            # Route to plan-and-execute for complex queries, otherwise ReAct
            if is_complex_query(user_message):
                generator = plan_and_execute(
                    self._kernel, chat_history, execution_settings, user_message
                )
            else:
                generator = run_react_loop(
                    self._kernel, chat_history, execution_settings
                )

            async for event in generator:
                if event.type == "token":
                    token_count += 1
                elif event.type == "source":
                    source_count += 1
                yield event

            duration_ms = int((time.time() - start) * 1000)
            track_event("agent.chat.response", {
                "client_name": client_name or "unknown",
                "source_count": source_count,
                "token_count": token_count,
                "duration_ms": duration_ms,
            })

        except Exception as e:
            logger.error("Agent error: %s", e)
            yield StreamEvent(type="error", message=str(e))
