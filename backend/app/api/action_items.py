from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models.action_item import ActionItem

router = APIRouter(prefix="/api/clients/{client_name}", tags=["action_items"])


@router.get("/action-items")
async def list_action_items(client_name: str, status: str = ""):
    repo = await _get_repo(client_name, "action_items")
    if status:
        items = await repo.query(
            "SELECT * FROM c WHERE c.status = @s",
            [{"name": "@s", "value": status}],
        )
    else:
        items = await repo.query("SELECT * FROM c", [])
    return {"action_items": items, "count": len(items)}


@router.get("/engagements/{engagement_id}/action-items")
async def list_engagement_action_items(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "action_items")
    items = await repo.query(
        "SELECT * FROM c WHERE c.engagement_id = @eid",
        [{"name": "@eid", "value": engagement_id}],
    )
    return {"action_items": items, "count": len(items)}


@router.post("/engagements/{engagement_id}/action-items")
async def create_action_item(client_name: str, engagement_id: str, body: ActionItem):
    body.engagement_id = engagement_id
    repo = await _get_repo(client_name, "action_items")
    result = await repo.upsert(body.model_dump(mode="json"))
    return result


@router.put("/action-items/{item_id}")
async def update_action_item(client_name: str, item_id: str, body: dict):
    repo = await _get_repo(client_name, "action_items")
    items = await repo.query("SELECT * FROM c WHERE c.id = @id", [{"name": "@id", "value": item_id}])
    if not items:
        raise HTTPException(status_code=404, detail="Action item not found")
    existing = items[0]
    existing.update(body)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    return await repo.upsert(existing)


async def _get_repo(client_name: str, container: str):
    from app.dependencies import get_cosmos_manager
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Services not available")
    client_id = client_name.lower().replace(" ", "-")
    return await manager.get_client_repo(client_id, container)
