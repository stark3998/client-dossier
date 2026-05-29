import logging
from fastapi import WebSocket

from app.models.event import ClientEvent

logger = logging.getLogger(__name__)


class NotificationManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)
        logger.info("Notification client connected (%d total)", len(self._connections))

    def disconnect(self, websocket: WebSocket):
        self._connections = [ws for ws in self._connections if ws is not websocket]
        logger.info("Notification client disconnected (%d remaining)", len(self._connections))

    async def broadcast(self, event: ClientEvent):
        payload = event.model_dump(mode="json")
        dead: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def active_connections(self) -> int:
        return len(self._connections)
