# backend/app/api/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness():
    return {"status": "ok"}


@router.get("/ready")
async def readiness():
    checks = {}
    overall = "ready"

    try:
        from app.dependencies import get_master_repo
        repo = get_master_repo()
        if repo is not None:
            checks["cosmos"] = "ok"
        else:
            checks["cosmos"] = "not configured"
    except Exception as e:
        checks["cosmos"] = f"error: {e}"
        overall = "degraded"

    try:
        from app.dependencies import get_search_service
        svc = get_search_service()
        if svc is not None:
            checks["search"] = "ok"
        else:
            checks["search"] = "not configured"
    except Exception as e:
        checks["search"] = f"error: {e}"
        overall = "degraded"

    return {"status": overall, "checks": checks}
