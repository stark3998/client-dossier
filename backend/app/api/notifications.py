import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.services.notification_manager import NotificationManager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["notifications"])

notification_manager = NotificationManager()


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    settings = get_settings()
    if not settings.LOCAL_MODE and not settings.BYPASS_AUTH:
        token = websocket.query_params.get("token", "")
        if not token:
            await websocket.close(code=4001, reason="Missing token")
            return

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
