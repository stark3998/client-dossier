import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class ReportingPlugin:
    def __init__(self, cosmos_manager):
        self._manager = cosmos_manager

    def _client_id(self, client_name: str) -> str:
        return client_name.lower().replace(" ", "-")

    @kernel_function(
        name="draft_status_report",
        description="Gather data for a status report on an engagement. Returns recent updates, deliverable progress, risks, and interaction summaries."
    )
    async def draft_status_report(self, client_name: str, engagement_id: str) -> str:
        cid = self._client_id(client_name)

        eng_repo = await self._manager.get_client_repo(cid, "engagements")
        engagement = await eng_repo.get(engagement_id, engagement_id)
        if not engagement:
            return json.dumps({"error": "Engagement not found"})

        status_repo = await self._manager.get_client_repo(cid, "status_updates")
        updates = await status_repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid ORDER BY c.date DESC",
            [{"name": "@eid", "value": engagement_id}],
        )

        del_repo = await self._manager.get_client_repo(cid, "deliverables")
        deliverables = await del_repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid",
            [{"name": "@eid", "value": engagement_id}],
        )

        risk_repo = await self._manager.get_client_repo(cid, "risks")
        risks = await risk_repo.query(
            "SELECT * FROM c WHERE c.engagement_id = @eid",
            [{"name": "@eid", "value": engagement_id}],
        )

        report_data = {
            "engagement": engagement,
            "recent_status_updates": updates[:5],
            "deliverables": deliverables,
            "deliverable_summary": {
                "total": len(deliverables),
                "draft": sum(1 for d in deliverables if d.get("status") == "draft"),
                "review": sum(1 for d in deliverables if d.get("status") == "review"),
                "delivered": sum(1 for d in deliverables if d.get("status") == "delivered"),
                "accepted": sum(1 for d in deliverables if d.get("status") == "accepted"),
            },
            "risks": risks,
            "open_risk_count": sum(1 for r in risks if r.get("status") == "open"),
        }
        return json.dumps(report_data, indent=2, default=str)

    @kernel_function(
        name="generate_meeting_summary",
        description="Generate a structured meeting summary from notes. Provide the raw notes and participant list."
    )
    async def generate_meeting_summary(
        self, client_name: str, notes: str, participants: str = ""
    ) -> str:
        summary = {
            "client": client_name,
            "participants": [p.strip() for p in participants.split(",") if p.strip()] if participants else [],
            "raw_notes": notes,
            "instruction": "Use the agent to summarize these notes, extract action items, and log the interaction.",
        }
        return json.dumps(summary, indent=2, default=str)
