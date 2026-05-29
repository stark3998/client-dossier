# app/agent/kernel.py
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)


async def create_kernel():
    from semantic_kernel import Kernel
    settings = get_settings()
    kernel = Kernel()

    if settings.LOCAL_MODE and not settings.AZURE_OPENAI_ENDPOINT:
        logger.info("LOCAL_MODE: Kernel created without LLM service")
        return kernel

    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
    chat_service = AzureChatCompletion(
        service_id="chat",
        deployment_name=settings.AZURE_OPENAI_DEPLOYMENT,
        endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_API_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )
    kernel.add_service(chat_service)
    logger.info("Kernel initialized with Azure OpenAI: %s", settings.AZURE_OPENAI_DEPLOYMENT)
    return kernel


def get_execution_settings():
    from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
    from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior

    return AzureChatPromptExecutionSettings(
        service_id="chat",
        max_tokens=4096,
        temperature=0.3,
        function_choice_behavior=FunctionChoiceBehavior.Auto(),
    )
