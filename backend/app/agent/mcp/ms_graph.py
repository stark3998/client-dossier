# app/agent/mcp/ms_graph.py
import json
from semantic_kernel.functions import kernel_function
from app.agent.mcp.base import MCPPluginBase


class MSGraphPlugin(MCPPluginBase):
    def __init__(self, endpoint: str = ""):
        super().__init__(name="MSGraph", endpoint=endpoint)

    async def connect(self) -> None:
        if self.endpoint:
            self._connected = True

    async def close(self) -> None:
        self._connected = False

    @kernel_function(
        name="search_ms_graph",
        description="Search Microsoft Graph for emails, calendar events, and files related to a client."
    )
    async def search(self, query: str, client_name: str = "") -> str:
        if not self._connected:
            return json.dumps({"message": "MS Graph MCP server is not configured. Enable via MCP_MS_GRAPH_ENABLED."})
        return json.dumps([{
            "type": "stub",
            "subject_or_title": f"Graph result for: {query}",
            "url": "https://graph.microsoft.com",
            "excerpt": "This is a stub response. Configure MCP_MS_GRAPH_ENDPOINT for real results.",
        }])
