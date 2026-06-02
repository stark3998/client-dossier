import logging

from fastapi import APIRouter, Request
from mcp.server.sse import SseServerTransport

from app.mcp_server.server import TOOL_DEFINITIONS, _caller_identity, mcp_server

logger = logging.getLogger(__name__)

mcp_router = APIRouter(tags=["MCP Server"])

# Message endpoint path must match the prefix used when the router is mounted.
# The router is mounted at "/mcp" in main.py, so the full path is /mcp/message.
_sse_transport = SseServerTransport("/mcp/message")


@mcp_router.get("/sse")
async def sse_endpoint(request: Request) -> None:
    """SSE stream endpoint. Establishes a persistent MCP session."""
    user = getattr(request.state, "user", {})
    token = _caller_identity.set(user)
    try:
        async with _sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,  # type: ignore[attr-defined]
        ) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )
    except Exception as exc:
        logger.warning("MCP SSE session error: %s", exc)
    finally:
        _caller_identity.reset(token)


@mcp_router.post("/message")
async def message_endpoint(request: Request) -> None:
    """JSON-RPC message endpoint for active SSE sessions."""
    await _sse_transport.handle_post_message(
        request.scope,
        request.receive,
        request._send,  # type: ignore[attr-defined]
    )


@mcp_router.get("/tools")
async def list_tools_endpoint() -> dict:
    """Return tool manifest for agent discovery. Unauthenticated."""
    return {
        "tools": [t.model_dump() for t in TOOL_DEFINITIONS],
        "count": len(TOOL_DEFINITIONS),
    }


@mcp_router.get("/health")
async def health_endpoint() -> dict:
    """Liveness probe. Unauthenticated."""
    return {"status": "ok", "transport": "http+sse", "tools": len(TOOL_DEFINITIONS)}
