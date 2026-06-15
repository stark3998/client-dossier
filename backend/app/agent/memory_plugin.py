# backend/app/agent/memory_plugin.py
import json
import logging
from datetime import datetime, timezone
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class MemoryPlugin:
    def __init__(self, cosmos_manager, search_service=None, embedding_service=None):
        self._manager = cosmos_manager
        self._search = search_service
        self._embeddings = embedding_service

    async def _get_repo(self, client_name: str):
        client_id = client_name.lower().replace(" ", "-")
        return await self._manager.get_client_repo(client_id, "memories")

    @kernel_function(
        name="recall_client_memory",
        description="Retrieve stored information about a client including stakeholders, engagements, action items, pain points, and strategic priorities."
    )
    async def recall_client_memory(self, client_name: str) -> str:
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._get_repo(client_name)
        memory = await repo.get(client_id, client_id)
        if memory is None:
            return json.dumps({"message": f"No memory found for client '{client_name}'"})
        return json.dumps(memory, indent=2, default=str)

    @kernel_function(
        name="update_client_memory",
        description="Store or update a specific field in client memory. field_name can be: industry, pain_points, strategic_priorities, financials_summary, active_engagements."
    )
    async def update_client_memory(self, client_name: str, field_name: str, value: str) -> str:
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._get_repo(client_name)
        memory = await repo.get(client_id, client_id)
        if memory is None:
            memory = {"id": client_id, "client_name": client_name}

        list_fields = {"pain_points", "strategic_priorities", "active_engagements", "sources"}
        if field_name in list_fields:
            existing = memory.get(field_name, [])
            if value not in existing:
                existing.append(value)
            memory[field_name] = existing
        else:
            memory[field_name] = value

        memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        await repo.upsert(memory)
        return json.dumps({"status": "updated", "field": field_name})

    @kernel_function(
        name="recall_engagements",
        description="List all engagements/projects for a client with their phase, status, and team."
    )
    async def recall_engagements(self, client_name: str) -> str:
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._manager.get_client_repo(client_id, "engagements")
        items = await repo.query("SELECT * FROM c", [])
        return json.dumps(items, indent=2, default=str)

    @kernel_function(
        name="recall_risks",
        description="List all risks for a client, optionally filtered by engagement."
    )
    async def recall_risks(self, client_name: str, engagement_id: str = "") -> str:
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._manager.get_client_repo(client_id, "risks")
        if engagement_id:
            items = await repo.query(
                "SELECT * FROM c WHERE c.engagement_id = @eid",
                [{"name": "@eid", "value": engagement_id}],
            )
        else:
            items = await repo.query("SELECT * FROM c", [])
        return json.dumps(items, indent=2, default=str)

    @kernel_function(
        name="recall_recent_interactions",
        description="List recent interactions (meetings, calls, emails) for a client."
    )
    async def recall_recent_interactions(self, client_name: str) -> str:
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._manager.get_client_repo(client_id, "interactions")
        items = await repo.query("SELECT * FROM c ORDER BY c.date DESC", [])
        return json.dumps(items[:20], indent=2, default=str)

    @kernel_function(
        name="create_engagement",
        description="Create a new engagement/project for a client. Provide name, phase, and description."
    )
    async def create_engagement(self, client_name: str, name: str, description: str = "", phase: str = "discovery") -> str:
        import uuid
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._manager.get_client_repo(client_id, "engagements")
        engagement = {
            "id": str(uuid.uuid4()),
            "name": name,
            "client_name": client_name,
            "phase": phase,
            "status": "active",
            "description": description,
            "team": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await repo.upsert(engagement)
        from app.agent.engagement_plugin import _index_record
        await _index_record("engagement", engagement, client_name, self._search, self._embeddings)
        return json.dumps({"status": "created", "engagement": engagement}, default=str)

    @kernel_function(
        name="log_interaction",
        description="Log a client interaction (meeting, call, email). Provide type, date, participants, and summary."
    )
    async def log_interaction(self, client_name: str, interaction_type: str, date: str, summary: str, participants: str = "") -> str:
        import uuid
        client_id = client_name.lower().replace(" ", "-")
        repo = await self._manager.get_client_repo(client_id, "interactions")
        interaction = {
            "id": str(uuid.uuid4()),
            "type": interaction_type,
            "date": date,
            "participants": [p.strip() for p in participants.split(",") if p.strip()] if participants else [],
            "summary": summary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await repo.upsert(interaction)
        return json.dumps({"status": "logged", "interaction": interaction}, default=str)
