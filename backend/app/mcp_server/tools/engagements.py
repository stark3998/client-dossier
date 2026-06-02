from app.dependencies import get_cosmos_manager


def _client_id(client_name: str) -> str:
    return client_name.lower().replace(" ", "-")


async def get_engagements(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    status = arguments.get("status", "all")
    include_risks = bool(arguments.get("include_risks", False))
    include_deliverables = bool(arguments.get("include_deliverables", False))

    if not client_name:
        raise ValueError("client_name is required")

    manager = get_cosmos_manager()
    if manager is None:
        raise RuntimeError("Cosmos service not initialized")

    cid = _client_id(client_name)
    repo = await manager.get_client_repo(cid, "engagements")

    if status == "all":
        engagements = await repo.query("SELECT * FROM c", [])
    else:
        engagements = await repo.query(
            "SELECT * FROM c WHERE c.status = @s",
            [{"name": "@s", "value": status}],
        )

    result: dict = {
        "client_name": client_name,
        "engagements": engagements,
        "count": len(engagements),
    }

    if include_risks and engagements:
        try:
            risks_repo = await manager.get_client_repo(cid, "risks")
            risks = await risks_repo.query("SELECT * FROM c", [])
            result["risks"] = risks
        except Exception:
            result["risks"] = []

    if include_deliverables and engagements:
        try:
            del_repo = await manager.get_client_repo(cid, "deliverables")
            deliverables = await del_repo.query("SELECT * FROM c", [])
            result["deliverables"] = deliverables
        except Exception:
            result["deliverables"] = []

    return result
