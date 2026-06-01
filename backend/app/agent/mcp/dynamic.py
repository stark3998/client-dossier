# backend/app/agent/mcp/dynamic.py
import json
import logging
from typing import Optional

import httpx
from semantic_kernel.functions import kernel_function

from app.agent.mcp.base import MCPPluginBase

logger = logging.getLogger(__name__)


class DynamicMCPPlugin(MCPPluginBase):
    """Generic MCP client supporting both custom REST and standard MCP SSE protocols."""

    def __init__(
        self,
        name: str,
        endpoint: str,
        auth_type: str = "none",
        auth_config: dict | None = None,
        protocol: str = "rest",
    ):
        super().__init__(name=name, endpoint=endpoint)
        self._auth_type = auth_type
        self._auth_config = auth_config or {}
        self._protocol = protocol  # "rest" or "sse"
        self._tools: list[dict] = []
        self._http_client: Optional[httpx.AsyncClient] = None
        # SSE session (mcp SDK) — only used when protocol == "sse"
        self._mcp_session = None
        self._mcp_exit_stack = None

    async def connect(self) -> None:
        if self._protocol == "sse":
            await self._connect_sse()
        else:
            await self._connect_rest()

    async def _connect_rest(self) -> None:
        headers = self._build_auth_headers()
        self._http_client = httpx.AsyncClient(
            base_url=self.endpoint, headers=headers, timeout=30.0
        )
        try:
            response = await self._http_client.get("/tools")
            if response.status_code == 200:
                data = response.json()
                self._tools = data.get("tools", [])
            self._connected = True
            logger.info("MCP (REST) '%s' connected: %d tools", self.name, len(self._tools))
        except Exception as e:
            logger.warning("MCP (REST) '%s' connection failed: %s", self.name, e)
            self._connected = False
            raise

    async def _connect_sse(self) -> None:
        try:
            from contextlib import AsyncExitStack
            from mcp import ClientSession
            from mcp.client.sse import sse_client

            headers = self._build_auth_headers()
            self._mcp_exit_stack = AsyncExitStack()
            read, write = await self._mcp_exit_stack.enter_async_context(
                sse_client(self.endpoint, headers=headers)
            )
            self._mcp_session = await self._mcp_exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await self._mcp_session.initialize()
            tools_response = await self._mcp_session.list_tools()
            self._tools = [
                {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
                for t in tools_response.tools
            ]
            self._connected = True
            logger.info("MCP (SSE) '%s' connected: %d tools", self.name, len(self._tools))
        except Exception as e:
            logger.warning("MCP (SSE) '%s' connection failed: %s", self.name, e)
            self._connected = False
            if self._mcp_exit_stack:
                await self._mcp_exit_stack.aclose()
                self._mcp_exit_stack = None
            raise

    async def close(self) -> None:
        if self._http_client:
            await self._http_client.aclose()
        if self._mcp_exit_stack:
            await self._mcp_exit_stack.aclose()
            self._mcp_exit_stack = None
        self._mcp_session = None
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
        if not self._connected:
            return json.dumps({"error": f"MCP server '{self.name}' is not connected"})
        if self._protocol == "sse":
            # For SSE servers, pick the first available tool if it looks like a search/query tool
            search_tools = [t["name"] for t in self._tools if any(
                kw in t["name"].lower() for kw in ("search", "query", "find", "lookup")
            )]
            tool = search_tools[0] if search_tools else (self._tools[0]["name"] if self._tools else None)
            if tool:
                return await self._invoke_sse(tool, {"query": query})
            return json.dumps({"error": "No suitable tool found on this server"})
        # REST path
        try:
            response = await self._http_client.post("/query", json={"query": query})
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return json.dumps({"error": f"Server returned {response.status_code}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="invoke_mcp_tool",
        description="Invoke a specific tool on this MCP server by name with JSON arguments.",
    )
    async def invoke_tool(self, tool_name: str, arguments_json: str = "{}") -> str:
        if not self._connected:
            return json.dumps({"error": f"MCP server '{self.name}' is not connected"})
        args = {}
        try:
            args = json.loads(arguments_json)
        except json.JSONDecodeError:
            pass
        if self._protocol == "sse":
            return await self._invoke_sse(tool_name, args)
        try:
            response = await self._http_client.post(
                f"/tools/{tool_name}/invoke", json={"arguments": args}
            )
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return json.dumps({"error": f"Tool invocation returned {response.status_code}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _invoke_sse(self, tool_name: str, arguments: dict) -> str:
        try:
            result = await self._mcp_session.call_tool(tool_name, arguments)
            content = result.content
            if isinstance(content, list):
                parts = []
                for item in content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    else:
                        parts.append(str(item))
                return json.dumps({"result": "\n".join(parts)}, indent=2)
            return json.dumps({"result": str(content)}, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="list_mcp_tools",
        description="List all tools available on this MCP server.",
    )
    async def list_tools(self) -> str:
        return json.dumps(self._tools, indent=2)
