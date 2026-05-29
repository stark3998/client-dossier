import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.notification_manager import NotificationManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notifications"])

notification_manager = NotificationManager()


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    await notification_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send ping or filter messages
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket)
    except Exception:
        notification_manager.disconnect(websocket)
