# backend/app/api/chat.py
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.message import ChatRequest, StreamEvent

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()

    settings = get_settings()
    if not settings.LOCAL_MODE:
        # Auth: expect token in query param
        token = websocket.query_params.get("token", "")
        if not token:
            await websocket.close(code=4001, reason="Missing token")
            return

    try:
        from app.dependencies import get_planner
        planner = get_planner()
    except (ImportError, Exception) as e:
        await websocket.send_json({"type": "error", "message": f"Agent not available: {e}"})
        await websocket.close()
        return

    if planner is None:
        await websocket.send_json({"type": "error", "message": "Agent not initialized"})
        await websocket.close()
        return

    from semantic_kernel.contents import ChatHistory
    chat_history = ChatHistory()
    from app.agent.planner import SYSTEM_PROMPT
    chat_history.add_system_message(SYSTEM_PROMPT)

    try:
        while True:
            data = await websocket.receive_json()
            request = ChatRequest(**data)

            async for event in planner.stream_response(
                chat_history=chat_history,
                user_message=request.content,
                client_name=request.client_name,
            ):
                await websocket.send_json(event.model_dump(exclude_none=True))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


@router.post("/api/chat")
async def rest_chat(request: ChatRequest):
    try:
        from app.dependencies import get_planner
        planner = get_planner()
    except (ImportError, Exception):
        return JSONResponse(status_code=503, content={"error": "Agent not available"})

    if planner is None:
        return JSONResponse(status_code=503, content={"error": "Agent not initialized"})

    from semantic_kernel.contents import ChatHistory
    chat_history = ChatHistory()
    from app.agent.planner import SYSTEM_PROMPT
    chat_history.add_system_message(SYSTEM_PROMPT)

    content_parts = []
    sources = []

    async for event in planner.stream_response(
        chat_history=chat_history,
        user_message=request.content,
        client_name=request.client_name,
    ):
        if event.type == "token" and event.content:
            content_parts.append(event.content)
        elif event.type == "source" and event.source:
            sources.append(event.source.model_dump())
        elif event.type == "error":
            return JSONResponse(status_code=500, content={"error": event.message})

    return {
        "content": "".join(content_parts),
        "sources": sources,
    }
