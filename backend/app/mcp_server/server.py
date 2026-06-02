import json
import time
import uuid
from contextvars import ContextVar

from mcp.server import Server
from mcp.types import TextContent, Tool

from app.mcp_server.logger import mcp_logger

# Caller identity injected per-request by router.py before MCP session runs
_caller_identity: ContextVar[dict] = ContextVar("mcp_caller_identity", default={})

mcp_server = Server("client-agent")

TOOL_DEFINITIONS: list[Tool] = [
    Tool(
        name="search_client_documents",
        description=(
            "Search indexed client documents using hybrid vector + BM25 search. "
            "Returns ranked chunks with source file, page, relevance score, and text content."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language search query"},
                "client_id": {"type": "string", "description": "Filter to a specific client (optional)"},
                "top_k": {"type": "integer", "description": "Number of results, default 5 max 20", "default": 5},
                "search_mode": {
                    "type": "string",
                    "enum": ["hybrid", "vector", "keyword"],
                    "default": "hybrid",
                    "description": "Search strategy (all modes use hybrid under the hood)",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="ingest_documents",
        description=(
            "Trigger document re-ingestion for a client from the OneDrive sync folder. "
            "Returns a job_id and initial status. Use mode='complete' to force full re-index."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name to ingest"},
                "mode": {
                    "type": "string",
                    "enum": ["incremental", "complete"],
                    "description": "incremental=new files only, complete=full re-index",
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Count files without writing (validation only)",
                },
            },
            "required": ["client_name", "mode"],
        },
    ),
    Tool(
        name="read_client_memory",
        description=(
            "Read structured client memory from Cosmos DB. Contains facts, stakeholders, "
            "engagements, pain points, and strategic priorities from document analysis."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Specific fields to return (omit for all fields)",
                },
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="write_client_memory",
        description="Update or append a field in the client memory record in Cosmos DB.",
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "field": {
                    "type": "string",
                    "description": "Memory field to update, e.g. 'pain_points', 'strategic_priorities'",
                },
                "value": {"description": "New value (string, list, or dict)"},
                "overwrite": {
                    "type": "boolean",
                    "default": False,
                    "description": "If false and field is a list, appends instead of replacing",
                },
            },
            "required": ["client_name", "field", "value"],
        },
    ),
    Tool(
        name="list_indexed_files",
        description="List metadata of files indexed in the document store for a client.",
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "page_size": {"type": "integer", "default": 20, "description": "Max 100"},
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="generate_insights",
        description=(
            "Retrieve structured insights for a client: memory, recent analyses, "
            "open risks, and overdue action items."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "insight_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["memory", "analyses", "risks", "action_items"],
                    },
                    "description": "Types to include (default: all)",
                },
                "max_insights": {"type": "integer", "default": 10, "description": "Max items per type (max 50)"},
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="get_client_communications",
        description=(
            "Retrieve emails, meetings, and draft replies for a client from the "
            "scanned communication store (Outlook/Graph API)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "comm_type": {
                    "type": "string",
                    "enum": ["emails", "meetings", "drafts", "all"],
                    "default": "all",
                },
                "limit": {"type": "integer", "default": 20, "description": "Max items per type (max 100)"},
                "lookback_days": {
                    "type": "integer",
                    "description": "Days to look back (default 7 for emails, 30 for meetings)",
                },
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="get_engagements",
        description="List engagements for a client, optionally including risks and deliverables.",
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["active", "completed", "all"],
                    "default": "all",
                },
                "include_risks": {"type": "boolean", "default": False},
                "include_deliverables": {"type": "boolean", "default": False},
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="get_client_timeline",
        description=(
            "Retrieve the unified chronological timeline of all events for a client: "
            "interactions, status updates, and document analyses."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
                "event_types": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["interaction", "status_update", "analysis"],
                    },
                    "description": "Filter by event type (omit for all types)",
                },
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="get_action_items",
        description="List action items for a client, optionally filtered by status or engagement.",
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "all",
                },
                "engagement_id": {
                    "type": "string",
                    "description": "Filter by engagement ID (optional)",
                },
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="get_client_health",
        description=(
            "Compute and retrieve the health score for a client, including risk level, "
            "engagement status, and overdue action items."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
            },
            "required": ["client_name"],
        },
    ),
    Tool(
        name="generate_briefing",
        description=(
            "Generate an executive briefing for a client summarising recent analyses, "
            "overdue action items, risk changes, and engagement updates."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "client_name": {"type": "string"},
                "since": {
                    "type": "string",
                    "description": "ISO date string to filter recent changes (optional)",
                },
            },
            "required": ["client_name"],
        },
    ),
]

_TOOL_DISPATCH: dict = {}


def _build_dispatch() -> None:
    from app.mcp_server.tools.search import search_client_documents
    from app.mcp_server.tools.ingest import ingest_documents
    from app.mcp_server.tools.memory import read_client_memory, write_client_memory
    from app.mcp_server.tools.files import list_indexed_files
    from app.mcp_server.tools.insights import generate_insights
    from app.mcp_server.tools.communications import get_client_communications
    from app.mcp_server.tools.engagements import get_engagements
    from app.mcp_server.tools.timeline import get_client_timeline
    from app.mcp_server.tools.action_items import get_action_items
    from app.mcp_server.tools.client_health import get_client_health
    from app.mcp_server.tools.briefing import generate_briefing

    _TOOL_DISPATCH.update({
        "search_client_documents": search_client_documents,
        "ingest_documents": ingest_documents,
        "read_client_memory": read_client_memory,
        "write_client_memory": write_client_memory,
        "list_indexed_files": list_indexed_files,
        "generate_insights": generate_insights,
        "get_client_communications": get_client_communications,
        "get_engagements": get_engagements,
        "get_client_timeline": get_client_timeline,
        "get_action_items": get_action_items,
        "get_client_health": get_client_health,
        "generate_briefing": generate_briefing,
    })


@mcp_server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOL_DEFINITIONS


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if not _TOOL_DISPATCH:
        _build_dispatch()

    trace_id = str(uuid.uuid4())
    start = time.monotonic()
    caller = _caller_identity.get({})

    mcp_logger.log_event(
        "tool_call_start",
        tool=name,
        trace_id=trace_id,
        caller=caller,
        input_data=arguments,
    )

    handler = _TOOL_DISPATCH.get(name)
    if handler is None:
        error_body = json.dumps({
            "error": {"code": "NOT_FOUND", "message": f"Unknown tool: {name}", "trace_id": trace_id}
        })
        mcp_logger.log_event("tool_call_error", tool=name, trace_id=trace_id, caller=caller,
                              duration_ms=(time.monotonic() - start) * 1000,
                              error=ValueError(f"Unknown tool: {name}"))
        return [TextContent(type="text", text=error_body)]

    try:
        result = await handler(arguments)
        duration_ms = (time.monotonic() - start) * 1000
        mcp_logger.log_event(
            "tool_call_success",
            tool=name,
            trace_id=trace_id,
            caller=caller,
            duration_ms=duration_ms,
        )
        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as exc:
        duration_ms = (time.monotonic() - start) * 1000
        mcp_logger.log_event(
            "tool_call_error",
            tool=name,
            trace_id=trace_id,
            caller=caller,
            duration_ms=duration_ms,
            error=exc,
        )
        error_body = json.dumps({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "trace_id": trace_id,
            }
        })
        return [TextContent(type="text", text=error_body)]
