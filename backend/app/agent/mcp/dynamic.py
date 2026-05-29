# backend/app/agent/mcp/dynamic.py
import json
import logging
from typing import Optional

import httpx
from semantic_kernel.functions import kernel_function

from app.agent.mcp.base import MCPPluginBase

logger = logging.getLogger(__name__)


class DynamicMCPPlugin(MCPPluginBase):
    """Generic MCP client that connects to any MCP-compliant HTTP endpoint."""

    def __init__(
        self,
        name: str,
        endpoint: str,
        auth_type: str = "none",
        auth_config: dict | None = None,
    ):
        super().__init__(name=name, endpoint=endpoint)
        self._auth_type = auth_type
        self._auth_config = auth_config or {}
        self._tools: list[dict] = []
        self._http_client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        headers = self._build_auth_headers()
        self._http_client = httpx.AsyncClient(
            base_url=self.endpoint, headers=headers, timeout=30.0
        )
        try:
            # Try to discover tools from the MCP endpoint
            response = await self._http_client.get("/tools")
            if response.status_code == 200:
                data = response.json()
                self._tools = data.get("tools", [])
            self._connected = True
            logger.info(
                "MCP server '%s' connected: %d tools", self.name, len(self._tools)
            )
        except Exception as e:
            logger.warning("MCP server '%s' connection failed: %s", self.name, e)
            self._connected = False
            raise

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        self._connected = False

    def _build_auth_headers(self) -> dict:
        if self._auth_type == "api_key":
            header = self._auth_config.get("header_name", "X-API-Key")
            return {header: self._auth_config.get("api_key", "")}
        elif self._auth_type == "bearer":
            return {"Authorization": f"Bearer {self._auth_config.get('token', '')}"}
        return {}

    @kernel_function(
        name="query_mcp_server",
        description="Query this MCP server with a natural language request.",
    )
    async def query(self, query: str) -> str:
        if not self._connected or not self._http_client:
            return json.dumps({"error": f"MCP server '{self.name}' is not connected"})

        try:
            response = await self._http_client.post(
                "/query",
                json={"query": query},
            )
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return json.dumps({"error": f"Server returned {response.status_code}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="invoke_mcp_tool",
        description="Invoke a specific tool on this MCP server by name with arguments.",
    )
    async def invoke_tool(self, tool_name: str, arguments_json: str = "{}") -> str:
        if not self._connected or not self._http_client:
            return json.dumps({"error": f"MCP server '{self.name}' is not connected"})

        try:
            args = json.loads(arguments_json)
            response = await self._http_client.post(
                f"/tools/{tool_name}/invoke",
                json={"arguments": args},
            )
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return json.dumps(
                {"error": f"Tool invocation returned {response.status_code}"}
            )
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="list_mcp_tools",
        description="List all tools available on this MCP server.",
    )
    async def list_tools(self) -> str:
        return json.dumps(self._tools, indent=2)
