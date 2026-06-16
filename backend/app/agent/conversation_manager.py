import logging

from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 8000
KEEP_RECENT = 6
SUMMARY_TAG = "[CONVERSATION_SUMMARY]"


class ConversationManager:
    def __init__(self, kernel=None):
        self._kernel = kernel
        self._enc = None

    def _get_encoder(self):
        if self._enc is None:
            try:
                import tiktoken
                self._enc = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                self._enc = None
        return self._enc

    def _count_tokens(self, text: str) -> int:
        enc = self._get_encoder()
        if enc:
            return len(enc.encode(text))
        return len(text) // 4

    def _count_history_tokens(self, chat_history) -> int:
        total = 0
        for msg in chat_history:
            total += self._count_tokens(str(msg.content))
        return total

    async def maybe_summarize(self, chat_history) -> bool:
        total = self._count_history_tokens(chat_history)
        if total <= TOKEN_BUDGET:
            return False

        messages = list(chat_history)
        system_msgs = [m for m in messages if (m.role.value == "system" if hasattr(m.role, 'value') else str(m.role) == "system")]
        non_system = [m for m in messages if not (m.role.value == "system" if hasattr(m.role, 'value') else str(m.role) == "system")]

        if len(non_system) <= KEEP_RECENT:
            return False

        to_summarize = non_system[:-KEEP_RECENT]
        to_keep = non_system[-KEEP_RECENT:]

        summary_text = await self._summarize_messages(to_summarize)
        if not summary_text:
            return False

        # Rebuild chat history
        while len(chat_history) > 0:
            try:
                chat_history.remove_message(chat_history[-1])
            except Exception:
                break

        for sm in system_msgs:
            if SUMMARY_TAG not in str(sm.content):
                chat_history.add_system_message(str(sm.content))

        chat_history.add_system_message(f"{SUMMARY_TAG}\n{summary_text}")

        for msg in to_keep:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            if role == "user":
                chat_history.add_user_message(str(msg.content))
            elif role == "assistant":
                chat_history.add_assistant_message(str(msg.content))

        logger.info("Conversation summarized: %d messages -> summary + %d recent", len(to_summarize), len(to_keep))
        return True

    async def _summarize_messages(self, messages) -> str:
        if not self._kernel:
            return self._basic_summarize(messages)

        try:
            from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
            from semantic_kernel.contents import ChatHistory
            from app.agent.kernel import get_execution_settings

            chat_service = self._kernel.get_service(type=ChatCompletionClientBase)
            conversation_text = "\n".join(
                f"{msg.role.value if hasattr(msg.role, 'value') else msg.role}: {str(msg.content)[:500]}"
                for msg in messages
            )

            prompt = load_prompt("summarize_conversation_prompt.txt")
            history = ChatHistory()
            history.add_user_message(prompt + conversation_text)

            settings = get_execution_settings(auto_invoke=True)
            settings.max_completion_tokens = 1024

            result = ""
            response = chat_service.get_streaming_chat_message_content(
                chat_history=history,
                settings=settings,
                kernel=self._kernel,
            )
            async for chunk in response:
                result += str(chunk)

            return result.strip()
        except Exception as e:
            logger.warning("LLM summarization failed: %s", e)
            return self._basic_summarize(messages)

    def _basic_summarize(self, messages) -> str:
        parts = []
        for msg in messages[-10:]:
            role = msg.role.value if hasattr(msg.role, 'value') else str(msg.role)
            content = str(msg.content)[:200]
            parts.append(f"{role}: {content}")
        return "Previous conversation summary:\n" + "\n".join(parts)
