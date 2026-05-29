# app/agent/mcp/ms_learn.py
import json
from semantic_kernel.functions import kernel_function
from app.agent.mcp.base import MCPPluginBase


class MSLearnPlugin(MCPPluginBase):
    def __init__(self, endpoint: str = ""):
        super().__init__(name="MSLearn", endpoint=endpoint)

    async def connect(self) -> None:
        if self.endpoint:
            self._connected = True

    async def close(self) -> None:
        self._connected = False

    @kernel_function(
        name="search_ms_learn",
        description="Search Microsoft Learn documentation for technical guidance and best practices."
    )
    async def search(self, query: str) -> str:
        if not self._connected:
            return json.dumps({"message": "MS Learn MCP server is not configured. Enable via MCP_MS_LEARN_ENABLED."})
        # Stub: real implementation would call the MCP SSE endpoint
        return json.dumps([{
            "title": f"MS Learn result for: {query}",
            "url": "https://learn.microsoft.com",
            "excerpt": "This is a stub response. Configure MCP_MS_LEARN_ENDPOINT for real results.",
        }])
