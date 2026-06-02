from app.dependencies import get_client_action_items_repo, get_cosmos_manager


async def get_action_items(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    status = arguments.get("status", "all")
    engagement_id = arguments.get("engagement_id")

    if not client_name:
        raise ValueError("client_name is required")

    repo = await get_client_action_items_repo(client_name)
    if repo is None:
        raise RuntimeError("Action items service not initialized")

    if engagement_id:
        items = await repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid",
            [{"name": "@eid", "value": engagement_id}],
        )
    elif status == "all":
        items = await repo.query("SELECT * FROM c", [])
    else:
        items = await repo.query(
            "SELECT * FROM c WHERE c.status = @s",
            [{"name": "@s", "value": status}],
        )

    return {"client_name": client_name, "action_items": items, "count": len(items)}
