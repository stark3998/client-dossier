# backend/app/api/tools.py
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.custom_tool import CustomTool

router = APIRouter(prefix="/api/tools", tags=["tools"])


@router.get("")
async def list_tools():
    """List all available tools (built-in + custom)."""
    manager = _get_manager()
    return {"tools": manager.list_all_tools()}


@router.get("/{plugin_name}/{function_name}")
async def get_tool_detail(plugin_name: str, function_name: str):
    """Get detailed info about a specific tool."""
    manager = _get_manager()
    detail = manager.get_tool_detail(plugin_name, function_name)
    if not detail:
        raise HTTPException(status_code=404, detail="Tool not found")
    return detail


@router.post("/invoke")
async def invoke_tool(body: dict):
    """Invoke a tool by plugin and function name with arguments."""
    manager = _get_manager()
    plugin = body.get("plugin", "")
    function = body.get("function", "")
    arguments = body.get("arguments", {})

    if not plugin or not function:
        raise HTTPException(status_code=400, detail="plugin and function are required")

    try:
        result = await manager.invoke_tool(plugin, function, arguments)
        return {"result": result, "plugin": plugin, "function": function}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/custom")
async def create_custom_tool(body: CustomTool):
    """Create a new custom prompt-based tool."""
    manager = _get_manager()
    body.created_at = datetime.now(timezone.utc)
    body.updated_at = datetime.now(timezone.utc)
    tool = await manager.register_custom_tool(body)
    return tool.model_dump(mode="json")


@router.put("/custom/{tool_id}")
async def update_custom_tool(tool_id: str, body: dict):
    """Update a custom tool."""
    manager = _get_manager()
    try:
        tool = await manager.update_custom_tool(tool_id, body)
        return tool.model_dump(mode="json")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/custom/{tool_id}")
async def delete_custom_tool(tool_id: str):
    """Delete a custom tool."""
    manager = _get_manager()
    await manager.unregister_custom_tool(tool_id)
    return {"status": "deleted"}


def _get_manager():
    from app.dependencies import get_tool_manager

    manager = get_tool_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Tool manager not initialized")
    return manager
