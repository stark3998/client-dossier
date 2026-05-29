# backend/app/dependencies.py
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

_cosmos_manager = None
_search_service = None
_embedding_service = None
_planner = None
_watcher = None
_tool_manager = None
_mcp_manager = None


async def startup_services():
    global _cosmos_manager, _search_service, _embedding_service, _planner, _watcher, _tool_manager, _mcp_manager

    settings = get_settings()
    logger.info("Initializing services (LOCAL_MODE=%s)", settings.LOCAL_MODE)

    # Cosmos client manager (master + per-client databases)
    from app.services.cosmos import create_client_manager
    _cosmos_manager = create_client_manager()
    await _cosmos_manager.initialize()

    # Search service
    from app.services.search import create_search_service
    _search_service = create_search_service()
    await _search_service.initialize()

    # Embedding service
    from app.services.embeddings import create_embedding_service
    _embedding_service = create_embedding_service()
    await _embedding_service.initialize()

    # Agent kernel + plugins
    from app.agent.kernel import create_kernel
    kernel = await create_kernel()

    from app.agent.search_plugin import SearchPlugin
    from app.agent.memory_plugin import MemoryPlugin
    from app.agent.file_plugin import FilePlugin
    from app.agent.docgen_plugin import DocumentGenerationPlugin

    plugins = {
        "Search": SearchPlugin(_search_service, _embedding_service),
        "Memory": MemoryPlugin(_cosmos_manager),
        "Files": FilePlugin(),
        "DocumentGeneration": DocumentGenerationPlugin(),
    }

    from app.agent.planner import AgentPlanner
    _planner = AgentPlanner(kernel, plugins)

    # MCP Manager (dynamic server management)
    from app.services.mcp_manager import MCPManager
    _mcp_manager = MCPManager(kernel, _cosmos_manager)
    await _mcp_manager.load_saved_servers()

    # Tool manager (custom tools from Cosmos + kernel functions)
    from app.services.tool_manager import ToolManager
    _tool_manager = ToolManager(kernel, _cosmos_manager)
    await _tool_manager.load_saved_tools()

    # File watcher (optional)
    import os
    if os.path.isdir(settings.ONEDRIVE_SYNC_PATH):
        from app.ingestion.watcher import FileWatcher
        _watcher = FileWatcher(settings.ONEDRIVE_SYNC_PATH)
        _watcher.start()

    logger.info("All services initialized")


async def shutdown_services():
    global _watcher
    if _watcher:
        _watcher.stop()
    if _search_service:
        await _search_service.close()
    if _embedding_service:
        await _embedding_service.close()
    if _cosmos_manager:
        await _cosmos_manager.close()
    logger.info("All services shut down")


def get_cosmos_manager():
    return _cosmos_manager


def get_master_repo():
    if _cosmos_manager is None:
        return None
    return _cosmos_manager.get_master_repo()


async def get_client_memory_repo(client_name: str):
    if _cosmos_manager is None:
        return None
    client_id = client_name.lower().replace(" ", "-")
    return await _cosmos_manager.get_client_repo(client_id, "memories")


async def get_client_doc_index_repo(client_name: str):
    if _cosmos_manager is None:
        return None
    client_id = client_name.lower().replace(" ", "-")
    return await _cosmos_manager.get_client_repo(client_id, "doc_index")


async def get_client_analysis_repo(client_name: str):
    if _cosmos_manager is None:
        return None
    client_id = client_name.lower().replace(" ", "-")
    return await _cosmos_manager.get_client_repo(client_id, "analyses")


def get_search_service():
    return _search_service


def get_embedding_service():
    return _embedding_service


def get_planner():
    return _planner


def get_tool_manager():
    return _tool_manager


def get_mcp_manager():
    return _mcp_manager
