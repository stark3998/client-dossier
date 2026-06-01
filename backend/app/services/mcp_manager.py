# backend/app/services/mcp_manager.py
import logging
from typing import Optional

from app.agent.mcp.dynamic import DynamicMCPPlugin
from app.models.mcp_server import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPManager:
    def __init__(self, kernel, cosmos_manager):
        self._kernel = kernel
        self._cosmos_manager = cosmos_manager
        self._servers: dict[str, MCPServerConfig] = {}
        self._plugins: dict[str, DynamicMCPPlugin] = {}

    async def load_saved_servers(self):
        """Load all saved MCP server configs from master DB and register them."""
        try:
            repo = self._cosmos_manager.get_mcp_servers_repo()
            if repo is None:
                return
            configs = await repo.query("SELECT * FROM c WHERE c.enabled = true", [])
            for config_data in configs:
                try:
                    config = MCPServerConfig(**config_data)
                    await self.register_server(config, persist=False)
                except Exception as e:
                    logger.warning(
                        "Failed to load MCP server '%s': %s",
                        config_data.get("name"),
                        e,
                    )
        except Exception as e:
            logger.warning("Failed to load MCP servers from DB: %s", e)

    async def register_server(
        self, config: MCPServerConfig, persist: bool = True
    ) -> MCPServerConfig:
        """Register a new MCP server and add it to the kernel."""
        plugin = DynamicMCPPlugin(
            name=config.name,
            endpoint=config.endpoint,
            auth_type=config.auth_type,
            auth_config=config.auth_config,
            protocol=getattr(config, "protocol", "rest"),
        )

        try:
            await plugin.connect()
            config.status = "connected"
            config.last_error = None
        except Exception as e:
            config.status = "error"
            config.last_error = str(e)
            logger.warning("MCP server '%s' failed to connect: %s", config.name, e)

        # Register with kernel using sanitized plugin name
        plugin_name = f"MCP_{config.name.replace(' ', '_').replace('-', '_')}"
        self._kernel.add_plugin(plugin, plugin_name=plugin_name)

        self._servers[config.id] = config
        self._plugins[config.id] = plugin

        if persist:
            try:
                repo = self._cosmos_manager.get_mcp_servers_repo()
                if repo:
                    await repo.upsert(config.model_dump(mode="json"))
            except Exception as e:
                logger.warning("Failed to persist MCP server config: %s", e)

        logger.info("MCP server registered: %s (%s)", config.name, config.status)
        return config

    async def unregister_server(self, server_id: str) -> None:
        """Remove an MCP server from the kernel and delete from DB."""
        plugin = self._plugins.pop(server_id, None)
        config = self._servers.pop(server_id, None)

        if plugin:
            await plugin.close()

        try:
            repo = self._cosmos_manager.get_mcp_servers_repo()
            if repo and config:
                await repo.delete(server_id, server_id)
        except Exception as e:
            logger.warning("Failed to delete MCP server config: %s", e)

    async def test_connection(self, server_id: str) -> dict:
        """Test connectivity to an MCP server."""
        config = self._servers.get(server_id)
        if not config:
            return {"status": "error", "message": "Server not found"}

        plugin = DynamicMCPPlugin(
            name=config.name,
            endpoint=config.endpoint,
            auth_type=config.auth_type,
            auth_config=config.auth_config,
            protocol=getattr(config, "protocol", "rest"),
        )
        try:
            await plugin.connect()
            await plugin.close()
            return {"status": "connected", "message": "Connection successful"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_servers(self) -> list[dict]:
        """List all registered servers with their status."""
        return [
            {
                **config.model_dump(mode="json"),
                "plugin_registered": sid in self._plugins,
            }
            for sid, config in self._servers.items()
        ]

    def get_server(self, server_id: str) -> Optional[MCPServerConfig]:
        return self._servers.get(server_id)
