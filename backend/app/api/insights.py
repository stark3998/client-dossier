# backend/app/api/insights.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("")
async def get_insights(client_name: str):
    try:
        from app.dependencies import get_client_memory_repo
        repo = await get_client_memory_repo(client_name)
    except Exception:
        raise HTTPException(status_code=503, detail="Services not available")

    if repo is None:
        raise HTTPException(status_code=503, detail="Memory service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    memory = await repo.get(client_id, client_id)

    if memory is None:
        return {
            "client_name": client_name,
            "industry": None,
            "key_stakeholders": [],
            "active_engagements": [],
            "financials_summary": None,
            "pain_points": [],
            "strategic_priorities": [],
            "past_deliverables": [],
            "open_action_items": [],
            "sources": [],
        }

    return memory
