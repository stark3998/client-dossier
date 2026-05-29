# backend/app/services/tool_manager.py
import logging
from datetime import datetime, timezone

from app.models.custom_tool import CustomTool

logger = logging.getLogger(__name__)


class ToolManager:
    def __init__(self, kernel, cosmos_manager):
        self._kernel = kernel
        self._cosmos_manager = cosmos_manager
        self._custom_tools: dict[str, CustomTool] = {}

    async def load_saved_tools(self):
        """Load all custom tools from master DB and register them."""
        try:
            repo = self._cosmos_manager.get_custom_tools_repo()
            if repo is None:
                return
            tools = await repo.query("SELECT * FROM c", [])
            for tool_data in tools:
                try:
                    tool = CustomTool(**tool_data)
                    self._register_prompt_function(tool)
                    self._custom_tools[tool.id] = tool
                except Exception as e:
                    logger.warning("Failed to load custom tool '%s': %s", tool_data.get("name"), e)
        except Exception as e:
            logger.warning("Failed to load custom tools: %s", e)

    async def register_custom_tool(self, tool: CustomTool) -> CustomTool:
        """Register a new custom tool and persist to Cosmos."""
        self._register_prompt_function(tool)
        self._custom_tools[tool.id] = tool

        try:
            repo = self._cosmos_manager.get_custom_tools_repo()
            if repo:
                await repo.upsert(tool.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Failed to persist custom tool: %s", e)

        logger.info("Custom tool registered: %s", tool.name)
        return tool

    async def unregister_custom_tool(self, tool_id: str) -> None:
        """Remove a custom tool."""
        tool = self._custom_tools.pop(tool_id, None)

        try:
            repo = self._cosmos_manager.get_custom_tools_repo()
            if repo and tool:
                await repo.delete(tool_id, tool_id)
        except Exception as e:
            logger.warning("Failed to delete custom tool: %s", e)

    async def update_custom_tool(self, tool_id: str, updates: dict) -> CustomTool:
        """Update an existing custom tool."""
        tool = self._custom_tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")

        updated = tool.model_copy(update=updates)
        updated.updated_at = datetime.now(timezone.utc)

        # Re-register the prompt function
        self._register_prompt_function(updated)
        self._custom_tools[tool_id] = updated

        try:
            repo = self._cosmos_manager.get_custom_tools_repo()
            if repo:
                await repo.upsert(updated.model_dump(mode="json"))
        except Exception as e:
            logger.warning("Failed to persist updated tool: %s", e)

        return updated

    def _register_prompt_function(self, tool: CustomTool):
        """Register a custom tool as a Semantic Kernel prompt function."""
        from semantic_kernel.functions import KernelFunctionFromPrompt

        func = KernelFunctionFromPrompt(
            function_name=tool.name,
            plugin_name="CustomTools",
            prompt=tool.prompt_template,
            description=tool.description,
        )
        self._kernel.add_function("CustomTools", func)

    def list_all_tools(self) -> list[dict]:
        """Enumerate all kernel plugins and their functions."""
        tools = []
        for plugin_name, plugin in self._kernel.plugins.items():
            for func_name, func in plugin.functions.items():
                tools.append({
                    "plugin": plugin_name,
                    "name": func_name,
                    "description": getattr(func, "description", ""),
                    "is_custom": plugin_name == "CustomTools",
                    "custom_tool_id": self._get_custom_tool_id(func_name),
                    "parameters": self._extract_parameters(func),
                })
        return tools

    def get_tool_detail(self, plugin_name: str, function_name: str) -> dict | None:
        """Get detailed info about a specific tool."""
        plugin = self._kernel.plugins.get(plugin_name)
        if not plugin:
            return None
        func = plugin.functions.get(function_name)
        if not func:
            return None
        return {
            "plugin": plugin_name,
            "name": function_name,
            "description": getattr(func, "description", ""),
            "is_custom": plugin_name == "CustomTools",
            "parameters": self._extract_parameters(func),
        }

    async def invoke_tool(self, plugin_name: str, function_name: str, arguments: dict) -> str:
        """Invoke a kernel function by name."""
        from semantic_kernel.functions import KernelArguments

        result = await self._kernel.invoke(
            plugin_name=plugin_name,
            function_name=function_name,
            arguments=KernelArguments(**arguments),
        )
        return str(result)

    def _get_custom_tool_id(self, func_name: str) -> str | None:
        for tid, tool in self._custom_tools.items():
            if tool.name == func_name:
                return tid
        return None

    def _extract_parameters(self, func) -> list[dict]:
        params = []
        metadata = getattr(func, "metadata", None)
        if metadata and hasattr(metadata, "parameters"):
            for p in metadata.parameters:
                params.append({
                    "name": p.name,
                    "description": getattr(p, "description", ""),
                    "type": getattr(p, "type_", "string"),
                    "required": getattr(p, "is_required", False),
                    "default": getattr(p, "default_value", None),
                })
        return params
