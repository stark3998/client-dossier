# backend/app/api/mcp.py
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.mcp_server import MCPServerConfig

router = APIRouter(prefix="/api/mcp/servers", tags=["mcp"])


@router.get("")
async def list_mcp_servers():
    manager = _get_manager()
    return {"servers": manager.list_servers()}


@router.post("")
async def add_mcp_server(body: MCPServerConfig):
    manager = _get_manager()
    body.created_at = datetime.now(timezone.utc)
    body.updated_at = datetime.now(timezone.utc)
    config = await manager.register_server(body)
    return config.model_dump(mode="json")


@router.get("/{server_id}")
async def get_mcp_server(server_id: str):
    manager = _get_manager()
    config = manager.get_server(server_id)
    if not config:
        raise HTTPException(status_code=404, detail="Server not found")
    return config.model_dump(mode="json")


@router.put("/{server_id}")
async def update_mcp_server(server_id: str, body: dict):
    manager = _get_manager()
    config = manager.get_server(server_id)
    if not config:
        raise HTTPException(status_code=404, detail="Server not found")

    # Unregister old, register new
    await manager.unregister_server(server_id)
    updated = config.model_copy(update=body)
    updated.id = server_id
    updated.updated_at = datetime.now(timezone.utc)
    result = await manager.register_server(updated)
    return result.model_dump(mode="json")


@router.delete("/{server_id}")
async def delete_mcp_server(server_id: str):
    manager = _get_manager()
    await manager.unregister_server(server_id)
    return {"status": "deleted"}


@router.post("/{server_id}/test")
async def test_mcp_server(server_id: str):
    manager = _get_manager()
    result = await manager.test_connection(server_id)
    return result


def _get_manager():
    from app.dependencies import get_mcp_manager

    manager = get_mcp_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="MCP manager not initialized")
    return manager
