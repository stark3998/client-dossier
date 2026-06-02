from app.dependencies import get_cosmos_manager


async def get_clients(arguments: dict) -> dict:
    """Return all client names and IDs from the master database."""
    cosmos_manager = get_cosmos_manager()
    if cosmos_manager is None:
        return {"clients": [], "error": "Cosmos manager not initialized"}

    try:
        repo = cosmos_manager.get_master_repo()
        if repo is None:
            return {"clients": []}
        clients = await repo.query("SELECT c.id, c.name FROM c WHERE c.type = 'client'", [])
        return {"clients": clients, "count": len(clients)}
    except Exception as exc:
        return {"clients": [], "error": str(exc)}
