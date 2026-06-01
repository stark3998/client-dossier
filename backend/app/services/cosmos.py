# backend/app/services/cosmos.py
import json
import logging
import os
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


class CosmosRepository:
    """Async repository for a single Cosmos DB container."""

    def __init__(self, container_client):
        self._container = container_client

    async def upsert(self, item: dict) -> dict:
        return await self._container.upsert_item(item)

    async def get(self, item_id: str, partition_key: str) -> Optional[dict]:
        try:
            return await self._container.read_item(item=item_id, partition_key=partition_key)
        except Exception:
            return None

    async def query(self, query: str, parameters: list | None = None, partition_key: str | None = None) -> list[dict]:
        kwargs: dict[str, Any] = {"query": query}
        if parameters:
            kwargs["parameters"] = parameters
        if partition_key is not None:
            kwargs["partition_key"] = partition_key
        items = []
        async for item in self._container.query_items(**kwargs):
            items.append(item)
        return items

    async def delete(self, item_id: str, partition_key: str) -> None:
        await self._container.delete_item(item=item_id, partition_key=partition_key)

    async def close(self):
        pass


class CosmosClientManager:
    """Manages master DB + per-client isolated databases."""

    def __init__(self):
        self._client = None
        self._master_db = None
        self._clients_container = None
        self._custom_tools_container = None
        self._mcp_servers_container = None
        self._ingest_jobs_container = None
        self._client_dbs: dict[str, Any] = {}

    async def initialize(self):
        settings = get_settings()
        from azure.cosmos.aio import CosmosClient
        from azure.cosmos import PartitionKey

        self._client = CosmosClient(settings.COSMOS_ENDPOINT, credential=settings.COSMOS_KEY)

        # Master database + clients container
        self._master_db = await self._client.create_database_if_not_exists(settings.COSMOS_DB_NAME)
        self._clients_container = await self._master_db.create_container_if_not_exists(
            id="clients",
            partition_key=PartitionKey(path="/id"),
        )
        self._custom_tools_container = await self._master_db.create_container_if_not_exists(
            id="custom_tools",
            partition_key=PartitionKey(path="/id"),
        )
        self._mcp_servers_container = await self._master_db.create_container_if_not_exists(
            id="mcp_servers",
            partition_key=PartitionKey(path="/id"),
        )
        self._ingest_jobs_container = await self._master_db.create_container_if_not_exists(
            id="ingest_jobs",
            partition_key=PartitionKey(path="/id"),
        )
        logger.info("Cosmos master DB initialized: %s", settings.COSMOS_DB_NAME)

    def get_master_repo(self) -> CosmosRepository:
        """Repository for the clients registry in the master database."""
        return CosmosRepository(self._clients_container)

    def get_custom_tools_repo(self) -> CosmosRepository | None:
        """Repository for custom tools in the master database."""
        if self._custom_tools_container is None:
            return None
        return CosmosRepository(self._custom_tools_container)

    def get_mcp_servers_repo(self) -> CosmosRepository | None:
        """Repository for MCP server configs in the master database."""
        if self._mcp_servers_container is None:
            return None
        return CosmosRepository(self._mcp_servers_container)

    def get_ingest_jobs_repo(self) -> CosmosRepository | None:
        """Repository for ingestion job state in the master database."""
        if self._ingest_jobs_container is None:
            return None
        return CosmosRepository(self._ingest_jobs_container)

    async def ensure_client_database(self, client_id: str) -> None:
        """Create a per-client database with standard containers if it doesn't exist."""
        from azure.cosmos import PartitionKey

        db_name = f"client_{client_id}"
        if db_name in self._client_dbs:
            return

        db = await self._client.create_database_if_not_exists(db_name)
        await db.create_container_if_not_exists(
            id="memories", partition_key=PartitionKey(path="/id")
        )
        await db.create_container_if_not_exists(
            id="doc_index", partition_key=PartitionKey(path="/file_path")
        )
        await db.create_container_if_not_exists(
            id="analyses", partition_key=PartitionKey(path="/file_path")
        )
        await db.create_container_if_not_exists(
            id="engagements", partition_key=PartitionKey(path="/id")
        )
        await db.create_container_if_not_exists(
            id="status_updates", partition_key=PartitionKey(path="/engagement_id")
        )
        await db.create_container_if_not_exists(
            id="deliverables", partition_key=PartitionKey(path="/engagement_id")
        )
        await db.create_container_if_not_exists(
            id="risks", partition_key=PartitionKey(path="/engagement_id")
        )
        await db.create_container_if_not_exists(
            id="interactions", partition_key=PartitionKey(path="/id")
        )
        await db.create_container_if_not_exists(
            id="events", partition_key=PartitionKey(path="/event_type")
        )
        await db.create_container_if_not_exists(
            id="action_items", partition_key=PartitionKey(path="/engagement_id")
        )
        self._client_dbs[db_name] = db
        logger.info("Client database ensured: %s", db_name)

    async def get_client_repo(self, client_id: str, container_name: str) -> CosmosRepository:
        """Get a repository for a specific container in a client's isolated database."""
        db_name = f"client_{client_id}"
        if db_name not in self._client_dbs:
            await self.ensure_client_database(client_id)
        db = self._client_dbs[db_name]
        container = db.get_container_client(container_name)
        return CosmosRepository(container)

    async def close(self):
        if self._client:
            await self._client.close()


class LocalCosmosRepository:
    """In-memory Cosmos DB stub for LOCAL_MODE."""

    def __init__(self, store_name: str):
        self._store_name = store_name
        self._store: dict[str, dict] = {}
        self._persist_path = os.path.join(
            get_settings().ONEDRIVE_SYNC_PATH, ".local_db", f"{store_name}.json"
        )

    async def initialize(self):
        if os.path.exists(self._persist_path):
            try:
                with open(self._persist_path, "r") as f:
                    self._store = json.load(f)
            except Exception:
                self._store = {}

    def _persist(self):
        os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
        with open(self._persist_path, "w") as f:
            json.dump(self._store, f, indent=2, default=str)

    async def upsert(self, item: dict) -> dict:
        self._store[item.get("id", "")] = item
        self._persist()
        return item

    async def get(self, item_id: str, partition_key: str) -> Optional[dict]:
        return self._store.get(item_id)

    async def query(self, query: str, parameters: list | None = None, partition_key: str | None = None) -> list[dict]:
        return list(self._store.values())

    async def delete(self, item_id: str, partition_key: str) -> None:
        self._store.pop(item_id, None)
        self._persist()

    async def close(self):
        pass


class LocalCosmosClientManager:
    """In-memory multi-database stub for LOCAL_MODE."""

    def __init__(self):
        self._master_repo = LocalCosmosRepository("master_clients")
        self._custom_tools_repo = LocalCosmosRepository("master_custom_tools")
        self._mcp_servers_repo = LocalCosmosRepository("master_mcp_servers")
        self._ingest_jobs_repo = LocalCosmosRepository("master_ingest_jobs")
        self._client_repos: dict[str, dict[str, LocalCosmosRepository]] = {}

    async def initialize(self):
        await self._master_repo.initialize()
        await self._custom_tools_repo.initialize()
        await self._mcp_servers_repo.initialize()
        await self._ingest_jobs_repo.initialize()

    def get_master_repo(self) -> LocalCosmosRepository:
        return self._master_repo

    def get_custom_tools_repo(self) -> LocalCosmosRepository:
        """Repository for custom tools in the local master database."""
        return self._custom_tools_repo

    def get_mcp_servers_repo(self) -> LocalCosmosRepository:
        """Repository for MCP server configs in the local master database."""
        return self._mcp_servers_repo

    def get_ingest_jobs_repo(self) -> LocalCosmosRepository:
        """Repository for ingestion job state in the local master database."""
        return self._ingest_jobs_repo

    async def ensure_client_database(self, client_id: str) -> None:
        if client_id not in self._client_repos:
            memories = LocalCosmosRepository(f"client_{client_id}_memories")
            doc_index = LocalCosmosRepository(f"client_{client_id}_doc_index")
            analyses = LocalCosmosRepository(f"client_{client_id}_analyses")
            engagements = LocalCosmosRepository(f"client_{client_id}_engagements")
            status_updates = LocalCosmosRepository(f"client_{client_id}_status_updates")
            deliverables = LocalCosmosRepository(f"client_{client_id}_deliverables")
            risks = LocalCosmosRepository(f"client_{client_id}_risks")
            interactions = LocalCosmosRepository(f"client_{client_id}_interactions")
            events = LocalCosmosRepository(f"client_{client_id}_events")
            action_items = LocalCosmosRepository(f"client_{client_id}_action_items")
            await memories.initialize()
            await doc_index.initialize()
            await analyses.initialize()
            await engagements.initialize()
            await status_updates.initialize()
            await deliverables.initialize()
            await risks.initialize()
            await interactions.initialize()
            await events.initialize()
            await action_items.initialize()
            self._client_repos[client_id] = {
                "memories": memories,
                "doc_index": doc_index,
                "analyses": analyses,
                "engagements": engagements,
                "status_updates": status_updates,
                "deliverables": deliverables,
                "risks": risks,
                "interactions": interactions,
                "events": events,
                "action_items": action_items,
            }

    async def get_client_repo(self, client_id: str, container_name: str) -> LocalCosmosRepository:
        await self.ensure_client_database(client_id)
        return self._client_repos[client_id][container_name]

    async def close(self):
        pass


def create_client_manager() -> CosmosClientManager | LocalCosmosClientManager:
    settings = get_settings()
    if settings.LOCAL_MODE:
        return LocalCosmosClientManager()
    return CosmosClientManager()
