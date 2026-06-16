# backend/app/main.py
from contextlib import asynccontextmanager
import logging

from app.telemetry import init_telemetry

init_telemetry()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import health, ingest, files, chat, insights, memory, clients, analysis, engagements, timeline, tools, mcp, action_items, client_health, notifications, briefing, communication
from app.api.auth import AuthMiddleware
from app.mcp_server.router import mcp_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    client_id_hint = f"...{settings.ENTRA_CLIENT_ID[-8:]}" if settings.ENTRA_CLIENT_ID else "(not set)"
    tenant_id_hint = f"...{settings.ENTRA_TENANT_ID[-8:]}" if settings.ENTRA_TENANT_ID else "(not set)"
    logger.info(
        "Starting Client Intelligence Agent | LOCAL_MODE=%s BYPASS_AUTH=%s "
        "ENTRA_CLIENT_ID=%s ENTRA_TENANT_ID=%s",
        settings.LOCAL_MODE, settings.BYPASS_AUTH, client_id_hint, tenant_id_hint,
    )
    # Startup: initialize services (will be wired in Phase 3)
    try:
        from app.dependencies import startup_services
        await startup_services()
    except ImportError:
        logger.info("Dependencies module not yet available, skipping service init")

    from app.mcp_server.logger import init_mcp_logger
    init_mcp_logger()
    yield
    # Shutdown: cleanup services
    try:
        from app.dependencies import shutdown_services
        await shutdown_services()
    except ImportError:
        pass
    logger.info("Shutdown complete")


app = FastAPI(
    title="Client Intelligence Agent",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

# Auth middleware (registered before CORS so it runs after CORS in request flow)
app.add_middleware(AuthMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:80"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrument after app creation
init_telemetry(app)

# Routers — health probes (no auth)
app.include_router(health.router)

# Routers — API endpoints
app.include_router(ingest.router)
app.include_router(files.router)
app.include_router(chat.router)
app.include_router(insights.router)
app.include_router(memory.router)
app.include_router(clients.router)
app.include_router(analysis.router)
app.include_router(engagements.router)
app.include_router(timeline.router)
app.include_router(tools.router)
app.include_router(mcp.router)
app.include_router(action_items.router)
app.include_router(client_health.router)
app.include_router(notifications.router)
app.include_router(briefing.router)
app.include_router(communication.router)
app.include_router(communication.ws_router)
app.include_router(mcp_router, prefix="/mcp")

# Configure logging — force=True overrides uvicorn's pre-installed handlers
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    force=True,
)
