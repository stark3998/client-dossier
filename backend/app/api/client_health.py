from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["health_scoring"])


@router.get("/api/clients/{client_name}/health")
async def get_client_health(client_name: str):
    from app.dependencies import get_cosmos_manager
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Services not available")

    from app.services.health_scorer import HealthScorer
    scorer = HealthScorer(manager)
    report = await scorer.compute_health(client_name)
    return report.model_dump(mode="json")
