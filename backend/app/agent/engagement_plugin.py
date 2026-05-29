import json
import logging
import uuid
from datetime import datetime, timezone
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)

VALID_PHASES = ["discovery", "design", "execute", "deliver", "sustain"]


class EngagementPlugin:
    def __init__(self, cosmos_manager, event_bus=None):
        self._manager = cosmos_manager
        self._event_bus = event_bus

    def _client_id(self, client_name: str) -> str:
        return client_name.lower().replace(" ", "-")

    async def _publish(self, client_name, event_type, entity_type, entity_id, summary, severity="info", metadata=None):
        if self._event_bus:
            from app.models.event import ClientEvent
            await self._event_bus.publish(ClientEvent(
                client_name=client_name,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                summary=summary,
                severity=severity,
                metadata=metadata or {},
            ))

    @kernel_function(
        name="create_risk",
        description="Create a new risk for a client engagement. Provide description, probability (1-5), impact (1-5), category, and engagement_id."
    )
    async def create_risk(
        self, client_name: str, description: str, probability: int = 3,
        impact: int = 3, category: str = "operational",
        engagement_id: str = "", mitigation: str = ""
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "risks")
        risk = {
            "id": str(uuid.uuid4()),
            "description": description,
            "probability": min(5, max(1, int(probability))),
            "impact": min(5, max(1, int(impact))),
            "category": category,
            "engagement_id": engagement_id,
            "mitigation": mitigation,
            "status": "open",
            "owner": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await repo.upsert(risk)
        severity_score = risk["probability"] * risk["impact"]
        sev = "critical" if severity_score >= 15 else "warning" if severity_score >= 8 else "info"
        await self._publish(client_name, "risk_created", "risk", risk["id"], description, sev)
        return json.dumps({"status": "created", "risk": risk, "severity_score": severity_score}, default=str)

    @kernel_function(
        name="update_risk",
        description="Update an existing risk. Provide risk_id, engagement_id (partition key), and fields to update as JSON."
    )
    async def update_risk(
        self, client_name: str, risk_id: str, engagement_id: str, updates_json: str = "{}"
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "risks")
        existing = await repo.get(risk_id, engagement_id)
        if not existing:
            return json.dumps({"error": "Risk not found"})
        updates = json.loads(updates_json) if updates_json else {}
        existing.update(updates)
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        await repo.upsert(existing)
        await self._publish(client_name, "risk_updated", "risk", risk_id, f"Risk updated: {existing.get('description', '')}")
        return json.dumps({"status": "updated", "risk": existing}, default=str)

    @kernel_function(
        name="create_deliverable",
        description="Create a new deliverable for an engagement."
    )
    async def create_deliverable(
        self, client_name: str, title: str, engagement_id: str,
        deliverable_type: str = "document", due_date: str = "", owner: str = ""
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "deliverables")
        deliverable = {
            "id": str(uuid.uuid4()),
            "title": title,
            "type": deliverable_type,
            "engagement_id": engagement_id,
            "status": "draft",
            "due_date": due_date,
            "owner": owner,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await repo.upsert(deliverable)
        await self._publish(client_name, "deliverable_created", "deliverable", deliverable["id"], title)
        return json.dumps({"status": "created", "deliverable": deliverable}, default=str)

    @kernel_function(
        name="update_deliverable_status",
        description="Update the status of a deliverable (draft/review/delivered/accepted)."
    )
    async def update_deliverable_status(
        self, client_name: str, deliverable_id: str, engagement_id: str, status: str
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "deliverables")
        existing = await repo.get(deliverable_id, engagement_id)
        if not existing:
            return json.dumps({"error": "Deliverable not found"})
        existing["status"] = status
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        await repo.upsert(existing)
        await self._publish(client_name, "deliverable_status_changed", "deliverable", deliverable_id, f"{existing['title']} -> {status}")
        return json.dumps({"status": "updated", "deliverable": existing}, default=str)

    @kernel_function(
        name="create_action_item",
        description="Create a tracked action item linked to an engagement."
    )
    async def create_action_item(
        self, client_name: str, description: str, owner: str = "",
        due_date: str = "", engagement_id: str = "", priority: str = "medium"
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "action_items")
        item = {
            "id": str(uuid.uuid4()),
            "description": description,
            "owner": owner,
            "due_date": due_date,
            "engagement_id": engagement_id,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await repo.upsert(item)
        await self._publish(client_name, "action_item_created", "action_item", item["id"], description)
        return json.dumps({"status": "created", "action_item": item}, default=str)

    @kernel_function(
        name="update_engagement_phase",
        description="Move an engagement to the next phase (discovery->design->execute->deliver->sustain)."
    )
    async def update_engagement_phase(
        self, client_name: str, engagement_id: str, new_phase: str
    ) -> str:
        if new_phase not in VALID_PHASES:
            return json.dumps({"error": f"Invalid phase. Must be one of: {VALID_PHASES}"})
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "engagements")
        existing = await repo.get(engagement_id, engagement_id)
        if not existing:
            return json.dumps({"error": "Engagement not found"})
        old_phase = existing.get("phase", "")
        existing["phase"] = new_phase
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()
        await repo.upsert(existing)
        await self._publish(
            client_name, "engagement_phase_changed", "engagement",
            engagement_id, f"{existing.get('name', '')} moved from {old_phase} to {new_phase}"
        )
        return json.dumps({"status": "updated", "engagement": existing}, default=str)

    @kernel_function(
        name="create_status_update",
        description="Log a status update for an engagement."
    )
    async def create_status_update(
        self, client_name: str, engagement_id: str, summary: str,
        sentiment: str = "neutral"
    ) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "status_updates")
        update = {
            "id": str(uuid.uuid4()),
            "engagement_id": engagement_id,
            "date": datetime.now(timezone.utc).isoformat(),
            "author": "agent",
            "summary": summary,
            "sentiment": sentiment,
        }
        await repo.upsert(update)
        await self._publish(client_name, "status_update_created", "status_update", update["id"], summary)
        return json.dumps({"status": "created", "update": update}, default=str)

    @kernel_function(
        name="recall_deliverables",
        description="List deliverables for an engagement."
    )
    async def recall_deliverables(self, client_name: str, engagement_id: str) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "deliverables")
        items = await repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid",
            [{"name": "@eid", "value": engagement_id}],
        )
        return json.dumps(items, indent=2, default=str)

    @kernel_function(
        name="recall_status_updates",
        description="List status updates for an engagement."
    )
    async def recall_status_updates(self, client_name: str, engagement_id: str) -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "status_updates")
        items = await repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid ORDER BY c.date DESC",
            [{"name": "@eid", "value": engagement_id}],
        )
        return json.dumps(items, indent=2, default=str)

    @kernel_function(
        name="query_analysis_results",
        description="Search past document analysis results for a client, optionally filtered by doc_type."
    )
    async def query_analysis_results(self, client_name: str, doc_type: str = "") -> str:
        cid = self._client_id(client_name)
        repo = await self._manager.get_client_repo(cid, "analyses")
        if doc_type:
            items = await repo.query(
                "SELECT * FROM c WHERE c.doc_type = @dt",
                [{"name": "@dt", "value": doc_type}],
            )
        else:
            items = await repo.query("SELECT * FROM c", [])
        return json.dumps(items, indent=2, default=str)
