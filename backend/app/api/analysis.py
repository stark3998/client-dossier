# backend/app/api/analysis.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/{client_name}")
async def list_analyses(client_name: str):
    """List all analysis results for a client."""
    try:
        from app.dependencies import get_client_analysis_repo
        repo = await get_client_analysis_repo(client_name)
    except Exception:
        raise HTTPException(status_code=503, detail="Services not available")

    if repo is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    results = await repo.query("SELECT * FROM c ORDER BY c.analyzed_at DESC", [])
    return {"results": results, "count": len(results)}


@router.get("/{client_name}/{analysis_id}")
async def get_analysis(client_name: str, analysis_id: str):
    """Get a specific analysis result."""
    try:
        from app.dependencies import get_client_analysis_repo
        repo = await get_client_analysis_repo(client_name)
    except Exception:
        raise HTTPException(status_code=503, detail="Services not available")

    if repo is None:
        raise HTTPException(status_code=503, detail="Analysis service not initialized")

    result = await repo.get(analysis_id, analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result
