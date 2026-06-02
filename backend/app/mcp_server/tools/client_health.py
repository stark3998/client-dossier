from app.dependencies import get_cosmos_manager


async def get_client_health(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")

    if not client_name:
        raise ValueError("client_name is required")

    manager = get_cosmos_manager()
    if manager is None:
        raise RuntimeError("Cosmos service not initialized")

    from app.services.health_scorer import HealthScorer
    scorer = HealthScorer(manager)
    report = await scorer.compute_health(client_name)
    return report.model_dump(mode="json")
