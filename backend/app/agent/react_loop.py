import json
import logging
from typing import AsyncGenerator

from app.models.message import StreamEvent, SourceChip

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 10


async def run_react_loop(
    kernel, chat_history, execution_settings
) -> AsyncGenerator[StreamEvent, None]:
    """ReAct-style agentic loop with manual tool invocation.

    Uses auto_invoke=False so we control the tool-call-and-retry cycle,
    emitting transparency events (thought, tool_call, tool_result) at each step.
    """
    from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
    from semantic_kernel.contents.function_call_content import FunctionCallContent
    from semantic_kernel.contents.streaming_chat_message_content import StreamingChatMessageContent

    chat_service = kernel.get_service(type=ChatCompletionClientBase)

    for iteration in range(MAX_ITERATIONS):
        # Collect streaming chunks into a full response
        full_text_parts: list[str] = []
        all_chunks: list[StreamingChatMessageContent] = []

        response = chat_service.get_streaming_chat_message_content(
            chat_history=chat_history,
            settings=execution_settings,
            kernel=kernel,
        )

        async for chunk in response:
            all_chunks.append(chunk)
            text = str(chunk)
            if text:
                full_text_parts.append(text)
                yield StreamEvent(type="token", content=text)

            # Extract sources from function results in stream
            if hasattr(chunk, "items"):
                for item in chunk.items:
                    if hasattr(item, "result") and item.result:
                        for source in _extract_sources(item.result):
                            yield StreamEvent(type="source", source=source)

        # Reduce chunks into a single message to inspect for function calls
        result_content = _reduce_chunks(all_chunks)
        if result_content is None:
            break

        # Check for function call requests
        function_calls = [
            item for item in (result_content.items if hasattr(result_content, "items") else [])
            if isinstance(item, FunctionCallContent)
        ]

        if not function_calls:
            # No tool calls — agent is done, add assistant message
            full_text = "".join(full_text_parts)
            if full_text:
                chat_history.add_assistant_message(full_text)
            break

        # Add the assistant message with function call metadata to history
        chat_history.add_message(result_content)

        # Execute each function call
        for fc in function_calls:
            tool_name = f"{fc.plugin_name}.{fc.function_name}" if fc.plugin_name else fc.function_name
            args = fc.arguments or {}
            tool_source = "mcp" if (fc.plugin_name or "").startswith("MCP_") else None

            yield StreamEvent(
                type="tool_call",
                tool_name=tool_name,
                tool_args=args,
                tool_source=tool_source,
                content=f"Calling {tool_name}",
            )

            try:
                result = await kernel.invoke_function_call(fc, chat_history)
                result_str = str(result) if result else ""
                # Truncate for display
                display = result_str[:500] + "..." if len(result_str) > 500 else result_str
                yield StreamEvent(
                    type="tool_result",
                    tool_name=tool_name,
                    tool_source=tool_source,
                    content=display,
                )
            except Exception as e:
                logger.warning("Tool call failed %s: %s", tool_name, e)
                yield StreamEvent(
                    type="tool_result",
                    tool_name=tool_name,
                    tool_source=tool_source,
                    content=f"Error: {e}",
                )

        if iteration < MAX_ITERATIONS - 1:
            yield StreamEvent(
                type="thought",
                content=f"Processing results from {len(function_calls)} tool(s)...",
            )

    yield StreamEvent(type="done")


def _reduce_chunks(chunks):
    """Reduce a list of streaming chunks into a single message content."""
    if not chunks:
        return None
    try:
        result = chunks[0]
        for chunk in chunks[1:]:
            result += chunk
        return result
    except Exception:
        return None


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
