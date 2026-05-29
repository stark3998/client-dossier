import json
import logging
import re
from typing import AsyncGenerator

from app.models.message import StreamEvent
from app.prompts.loader import load_prompt

logger = logging.getLogger(__name__)

COMPLEXITY_PATTERNS = re.compile(
    r"\b(compare|across all|for each|summarize all|every engagement|all clients|full report|comprehensive)\b",
    re.IGNORECASE,
)


def is_complex_query(query: str) -> bool:
    return bool(COMPLEXITY_PATTERNS.search(query)) or len(query) > 150


async def plan_and_execute(
    kernel, chat_history, execution_settings, user_message: str
) -> AsyncGenerator[StreamEvent, None]:
    """Create an explicit plan, then execute each step via the ReAct loop."""
    from app.agent.react_loop import run_react_loop
    from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

    planning_prompt = load_prompt("planning_prompt.txt")
    chat_service = kernel.get_service(type=ChatCompletionClientBase)

    # Step 1: Generate plan (non-streaming)
    yield StreamEvent(type="thought", content="This is a complex query — creating an execution plan...")

    from semantic_kernel.contents import ChatHistory
    from app.agent.kernel import get_execution_settings

    plan_history = ChatHistory()
    plan_history.add_system_message("You are a task planner. Return ONLY a JSON array of step descriptions.")
    plan_history.add_user_message(planning_prompt + user_message)

    plan_settings = get_execution_settings(auto_invoke=True)
    plan_settings.max_tokens = 1024
    plan_settings.temperature = 0.2

    plan_text = ""
    response = chat_service.get_streaming_chat_message_content(
        chat_history=plan_history,
        settings=plan_settings,
        kernel=kernel,
    )
    async for chunk in response:
        plan_text += str(chunk)

    # Parse plan
    try:
        steps = json.loads(plan_text)
        if not isinstance(steps, list):
            steps = [plan_text]
    except json.JSONDecodeError:
        steps = [plan_text.strip()]

    yield StreamEvent(type="plan", plan_steps=steps)

    # Step 2: Execute each step
    for i, step in enumerate(steps):
        yield StreamEvent(
            type="plan_step",
            content=step,
            step_number=i + 1,
            step_total=len(steps),
        )

        chat_history.add_user_message(f"[Plan step {i+1}/{len(steps)}]: {step}")

        async for event in run_react_loop(kernel, chat_history, execution_settings):
            if event.type != "done":
                yield event

    yield StreamEvent(type="done")
