# backend/app/api/engagements.py
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.models.engagement import Engagement, Deliverable, Risk, StatusUpdate, Interaction

router = APIRouter(prefix="/api/clients/{client_name}", tags=["engagements"])


# -- Engagements ---------------------------------------------------------------

@router.get("/engagements")
async def list_engagements(client_name: str):
    repo = await _get_repo(client_name, "engagements")
    items = await repo.query("SELECT * FROM c", [])
    return {"engagements": items, "count": len(items)}


@router.post("/engagements")
async def create_engagement(client_name: str, body: Engagement):
    body.client_name = client_name
    body.updated_at = datetime.now(timezone.utc)
    repo = await _get_repo(client_name, "engagements")
    result = await repo.upsert(body.model_dump(mode="json"))
    return result


@router.get("/engagements/{engagement_id}")
async def get_engagement(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "engagements")
    item = await repo.get(engagement_id, engagement_id)
    if not item:
        raise HTTPException(status_code=404, detail="Engagement not found")
    return item


@router.put("/engagements/{engagement_id}")
async def update_engagement(client_name: str, engagement_id: str, body: dict):
    repo = await _get_repo(client_name, "engagements")
    existing = await repo.get(engagement_id, engagement_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Engagement not found")
    existing.update(body)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    return await repo.upsert(existing)


@router.delete("/engagements/{engagement_id}")
async def delete_engagement(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "engagements")
    await repo.delete(engagement_id, engagement_id)
    return {"status": "deleted"}


# -- Deliverables --------------------------------------------------------------

@router.get("/engagements/{engagement_id}/deliverables")
async def list_deliverables(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "deliverables")
    items = await repo.query(
        "SELECT * FROM c WHERE c.engagement_id = @eid",
        [{"name": "@eid", "value": engagement_id}],
        partition_key=engagement_id,
    )
    return {"deliverables": items, "count": len(items)}


@router.post("/engagements/{engagement_id}/deliverables")
async def create_deliverable(client_name: str, engagement_id: str, body: Deliverable):
    body.engagement_id = engagement_id
    body.updated_at = datetime.now(timezone.utc)
    repo = await _get_repo(client_name, "deliverables")
    return await repo.upsert(body.model_dump(mode="json"))


@router.put("/deliverables/{deliverable_id}")
async def update_deliverable(client_name: str, deliverable_id: str, body: dict):
    repo = await _get_repo(client_name, "deliverables")
    engagement_id = body.get("engagement_id", "")
    existing = await repo.get(deliverable_id, engagement_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Deliverable not found")
    existing.update(body)
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    return await repo.upsert(existing)


# -- Risks --------------------------------------------------------------------

@router.get("/engagements/{engagement_id}/risks")
async def list_risks(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "risks")
    items = await repo.query(
        "SELECT * FROM c WHERE c.engagement_id = @eid",
        [{"name": "@eid", "value": engagement_id}],
        partition_key=engagement_id,
    )
    return {"risks": items, "count": len(items)}


@router.post("/engagements/{engagement_id}/risks")
async def create_risk(client_name: str, engagement_id: str, body: Risk):
    body.engagement_id = engagement_id
    body.updated_at = datetime.now(timezone.utc)
    repo = await _get_repo(client_name, "risks")
    return await repo.upsert(body.model_dump(mode="json"))


@router.get("/risks")
async def list_all_risks(client_name: str):
    repo = await _get_repo(client_name, "risks")
    items = await repo.query("SELECT * FROM c", [])
    return {"risks": items, "count": len(items)}


# -- Status Updates ------------------------------------------------------------

@router.get("/engagements/{engagement_id}/status-updates")
async def list_status_updates(client_name: str, engagement_id: str):
    repo = await _get_repo(client_name, "status_updates")
    items = await repo.query(
        "SELECT * FROM c WHERE c.engagement_id = @eid ORDER BY c.date DESC",
        [{"name": "@eid", "value": engagement_id}],
        partition_key=engagement_id,
    )
    return {"status_updates": items, "count": len(items)}


@router.post("/engagements/{engagement_id}/status-updates")
async def create_status_update(client_name: str, engagement_id: str, body: StatusUpdate):
    body.engagement_id = engagement_id
    repo = await _get_repo(client_name, "status_updates")
    return await repo.upsert(body.model_dump(mode="json"))


# -- Interactions --------------------------------------------------------------

@router.get("/interactions")
async def list_interactions(client_name: str):
    repo = await _get_repo(client_name, "interactions")
    items = await repo.query("SELECT * FROM c ORDER BY c.date DESC", [])
    return {"interactions": items, "count": len(items)}


@router.post("/interactions")
async def create_interaction(client_name: str, body: Interaction):
    repo = await _get_repo(client_name, "interactions")
    return await repo.upsert(body.model_dump(mode="json"))


# -- Helper --------------------------------------------------------------------

async def _get_repo(client_name: str, container: str):
    from app.dependencies import get_cosmos_manager
    manager = get_cosmos_manager()
    if manager is None:
        raise HTTPException(status_code=503, detail="Services not available")
    client_id = client_name.lower().replace(" ", "-")
    return await manager.get_client_repo(client_id, container)
