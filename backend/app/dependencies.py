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
_event_bus = None
_alert_checker = None
_communication_access = None
_communication_scanner = None


async def startup_services():
    global _cosmos_manager, _search_service, _embedding_service, _planner, _watcher, _tool_manager, _mcp_manager, _event_bus, _alert_checker, _communication_access, _communication_scanner

    settings = get_settings()
    logger.info("Initializing services (LOCAL_MODE=%s)", settings.LOCAL_MODE)

    # Cosmos client manager (master + per-client databases)
    from app.services.cosmos import create_client_manager
    _cosmos_manager = create_client_manager()
    await _cosmos_manager.initialize()

    # Event bus
    from app.services.event_bus import EventBus
    _event_bus = EventBus(_cosmos_manager)

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
    from app.agent.engagement_plugin import EngagementPlugin
    from app.agent.reporting_plugin import ReportingPlugin
    from app.agent.web_search_plugin import WebSearchPlugin
    from app.agent.query_rewriter import QueryRewriter

    search_plugin = SearchPlugin(_search_service, _embedding_service)
    rewriter = QueryRewriter(kernel, _embedding_service)
    search_plugin.set_rewriter(rewriter)

    # Communication services (win32com + Graph API)
    from app.services.outlook_win32 import OutlookWin32Service
    from app.services.graph_api_service import GraphAPIService
    from app.services.communication_access import CommunicationAccess
    _win32 = OutlookWin32Service()
    _graph = GraphAPIService(
        client_id=settings.GRAPH_CLIENT_ID,
        tenant_id=settings.GRAPH_TENANT_ID,
        client_secret=settings.GRAPH_CLIENT_SECRET,
        user_email=settings.GRAPH_USER_EMAIL,
    )
    _communication_access = CommunicationAccess(_win32, _graph)

    from app.agent.communication_plugin import CommunicationPlugin
    comm_plugin = CommunicationPlugin(_cosmos_manager, _communication_access)

    plugins = {
        "Search": search_plugin,
        "Memory": MemoryPlugin(_cosmos_manager),
        "Files": FilePlugin(),
        "DocumentGeneration": DocumentGenerationPlugin(),
        "Engagements": EngagementPlugin(_cosmos_manager, _event_bus),
        "Reporting": ReportingPlugin(_cosmos_manager),
        "WebSearch": WebSearchPlugin(settings),
        "Communication": comm_plugin,
    }

    from app.agent.planner import AgentPlanner
    _planner = AgentPlanner(kernel, plugins, cosmos_manager=_cosmos_manager)

    # MCP Manager (dynamic server management)
    from app.services.mcp_manager import MCPManager
    _mcp_manager = MCPManager(kernel, _cosmos_manager)
    await _mcp_manager.load_saved_servers()

    # Tool manager (custom tools from Cosmos + kernel functions)
    from app.services.tool_manager import ToolManager
    _tool_manager = ToolManager(kernel, _cosmos_manager)
    await _tool_manager.load_saved_tools()

    # Alert checker (proactive background monitoring)
    from app.agent.alert_checker import AlertChecker
    _alert_checker = AlertChecker(_cosmos_manager, _event_bus)
    await _alert_checker.start(interval_seconds=900)

    # Communication scanner (email + calendar background polling)
    from app.agent.communication_scanner import CommunicationScanner
    _communication_scanner = CommunicationScanner(
        _cosmos_manager, _communication_access, kernel, _event_bus
    )
    await _communication_scanner.start(interval_seconds=settings.COMM_SCAN_INTERVAL)

    # Subscribe notification manager to event bus for WebSocket push
    from app.api.notifications import notification_manager
    _event_bus.subscribe(notification_manager.broadcast)

    # File watcher (optional)
    import os
    if os.path.isdir(settings.ONEDRIVE_SYNC_PATH):
        from app.ingestion.watcher import FileWatcher
        _watcher = FileWatcher(settings.ONEDRIVE_SYNC_PATH)
        _watcher.start()

    logger.info("All services initialized")


async def shutdown_services():
    global _watcher, _alert_checker, _communication_scanner
    if _communication_scanner:
        await _communication_scanner.stop()
    if _alert_checker:
        await _alert_checker.stop()
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


def get_job_repo():
    if _cosmos_manager is None:
        return None
    return _cosmos_manager.get_ingest_jobs_repo()


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


def get_event_bus():
    return _event_bus


async def get_client_action_items_repo(client_name: str):
    if _cosmos_manager is None:
        return None
    client_id = client_name.lower().replace(" ", "-")
    return await _cosmos_manager.get_client_repo(client_id, "action_items")


async def get_client_events_repo(client_name: str):
    if _cosmos_manager is None:
        return None
    client_id = client_name.lower().replace(" ", "-")
    return await _cosmos_manager.get_client_repo(client_id, "events")


def get_communication_access():
    return _communication_access


def get_communication_scanner():
    return _communication_scanner
