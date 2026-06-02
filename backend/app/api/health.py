# backend/app/api/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness():
    return {"status": "ok"}


def _check(label: str, status: str, detail: str | None = None) -> dict:
    result: dict = {"label": label, "status": status}
    if detail:
        result["detail"] = detail
    return result


@router.get("/ready")
async def readiness():
    checks: dict[str, dict] = {}

    # ── Cosmos DB ──────────────────────────────────────────────────────────────
    try:
        from app.dependencies import get_master_repo
        repo = get_master_repo()
        checks["cosmos"] = _check("Cosmos DB", "ok" if repo else "not_configured")
    except Exception as e:
        checks["cosmos"] = _check("Cosmos DB", "error", str(e))

    # ── Azure AI Search ────────────────────────────────────────────────────────
    try:
        from app.dependencies import get_search_service
        svc = get_search_service()
        checks["search"] = _check("Azure AI Search", "ok" if svc else "not_configured")
    except Exception as e:
        checks["search"] = _check("Azure AI Search", "error", str(e))

    # ── Azure OpenAI / Embeddings ──────────────────────────────────────────────
    try:
        from app.dependencies import get_embedding_service
        emb = get_embedding_service()
        checks["openai"] = _check("Azure OpenAI", "ok" if emb else "not_configured")
    except Exception as e:
        checks["openai"] = _check("Azure OpenAI", "error", str(e))

    # ── AI Agent (planner) ─────────────────────────────────────────────────────
    try:
        from app.dependencies import get_planner
        planner = get_planner()
        checks["agent"] = _check("AI Agent", "ok" if planner else "not_configured")
    except Exception as e:
        checks["agent"] = _check("AI Agent", "error", str(e))

    # ── Microsoft Graph (communication) ───────────────────────────────────────
    try:
        from app.config import get_settings
        from app.dependencies import get_communication_access
        settings = get_settings()
        comm = get_communication_access()
        if comm and settings.GRAPH_CLIENT_ID and settings.GRAPH_CLIENT_SECRET:
            checks["graph"] = _check("Microsoft Graph", "ok")
        else:
            checks["graph"] = _check("Microsoft Graph", "not_configured")
    except Exception as e:
        checks["graph"] = _check("Microsoft Graph", "error", str(e))

    # ── Web Search (Tavily) ────────────────────────────────────────────────────
    try:
        from app.config import get_settings
        settings = get_settings()
        checks["web_search"] = _check(
            "Web Search",
            "ok" if settings.TAVILY_API_KEY else "not_configured",
        )
    except Exception as e:
        checks["web_search"] = _check("Web Search", "error", str(e))

    # ── OneDrive Sync ──────────────────────────────────────────────────────────
    try:
        import os
        from app.config import get_settings
        settings = get_settings()
        path_exists = os.path.isdir(settings.ONEDRIVE_SYNC_PATH)
        checks["onedrive"] = _check("OneDrive Sync", "ok" if path_exists else "not_configured")
    except Exception as e:
        checks["onedrive"] = _check("OneDrive Sync", "error", str(e))

    # ── MCP Servers ────────────────────────────────────────────────────────────
    try:
        from app.dependencies import get_mcp_manager
        mgr = get_mcp_manager()
        checks["mcp"] = _check("MCP Servers", "ok" if mgr else "not_configured")
    except Exception as e:
        checks["mcp"] = _check("MCP Servers", "error", str(e))

    overall = "degraded" if any(c["status"] == "error" for c in checks.values()) else "ready"
    return {"status": overall, "checks": checks}
