import asyncio
import logging
from typing import Callable, Optional

from app.models.event import ClientEvent

logger = logging.getLogger(__name__)


class EventBus:
    """In-process async event bus with Cosmos persistence and subscriber dispatch."""

    def __init__(self, cosmos_manager=None):
        self._cosmos_manager = cosmos_manager
        self._subscribers: list[Callable] = []

    def subscribe(self, callback: Callable) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        self._subscribers = [s for s in self._subscribers if s is not callback]

    async def publish(self, event: ClientEvent) -> None:
        if self._cosmos_manager:
            try:
                client_id = event.client_name.lower().replace(" ", "-")
                repo = await self._cosmos_manager.get_client_repo(client_id, "events")
                await repo.upsert(event.model_dump(mode="json"))
            except Exception as e:
                logger.warning("Failed to persist event %s: %s", event.id, e)

        for callback in self._subscribers:
            try:
                asyncio.create_task(callback(event))
            except Exception as e:
                logger.warning("Event subscriber error: %s", e)

    async def get_recent(
        self,
        client_name: str,
        event_types: Optional[list[str]] = None,
        since: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        if not self._cosmos_manager:
            return []

        client_id = client_name.lower().replace(" ", "-")
        try:
            repo = await self._cosmos_manager.get_client_repo(client_id, "events")
            query = "SELECT TOP @limit * FROM c"
            params = [{"name": "@limit", "value": limit}]

            if event_types:
                placeholders = ", ".join(f"@et{i}" for i in range(len(event_types)))
                query += f" WHERE c.event_type IN ({placeholders})"
                for i, et in enumerate(event_types):
                    params.append({"name": f"@et{i}", "value": et})

            if since:
                conjunction = " AND" if "WHERE" in query else " WHERE"
                query += f"{conjunction} c.created_at >= @since"
                params.append({"name": "@since", "value": since})

            query += " ORDER BY c.created_at DESC"
            return await repo.query(query, params)
        except Exception as e:
            logger.warning("Failed to query events for %s: %s", client_name, e)
            return []
