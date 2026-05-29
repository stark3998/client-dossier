import logging
from datetime import datetime, timezone

from app.models.health import (
    ClientHealthReport, EngagementHealth, RiskPosture, RelationshipHealth,
)

logger = logging.getLogger(__name__)


class HealthScorer:
    def __init__(self, cosmos_manager):
        self._manager = cosmos_manager

    async def compute_health(self, client_name: str) -> ClientHealthReport:
        client_id = client_name.lower().replace(" ", "-")
        now = datetime.now(timezone.utc)

        engagements = await self._query(client_id, "engagements")
        deliverables = await self._query(client_id, "deliverables")
        risks = await self._query(client_id, "risks")
        action_items = await self._query(client_id, "action_items")
        interactions = await self._query(client_id, "interactions")
        memory = await self._get_memory(client_id)

        eng_health = self._compute_engagement_health(engagements, deliverables, action_items, now)
        risk_post = self._compute_risk_posture(risks)
        rel_health = self._compute_relationship_health(interactions, memory, now)

        overall = eng_health.score * 0.40 + risk_post.score * 0.35 + rel_health.score * 0.25
        grade = self._score_to_grade(overall)

        alerts = []
        if eng_health.deliverables_overdue > 0:
            alerts.append(f"{eng_health.deliverables_overdue} overdue deliverable(s)")
        if eng_health.action_items_overdue > 0:
            alerts.append(f"{eng_health.action_items_overdue} overdue action item(s)")
        if risk_post.critical_risks > 0:
            alerts.append(f"{risk_post.critical_risks} critical risk(s)")
        if rel_health.days_since_last_interaction > 30:
            alerts.append(f"No interaction in {rel_health.days_since_last_interaction} days")

        return ClientHealthReport(
            client_name=client_name,
            overall_score=round(overall, 1),
            grade=grade,
            engagement_health=eng_health,
            risk_posture=risk_post,
            relationship_health=rel_health,
            computed_at=now,
            alerts=alerts,
        )

    def _compute_engagement_health(self, engagements, deliverables, action_items, now) -> EngagementHealth:
        phase_dist: dict[str, int] = {}
        for e in engagements:
            phase = e.get("phase", "unknown")
            phase_dist[phase] = phase_dist.get(phase, 0) + 1

        on_track = 0
        overdue = 0
        for d in deliverables:
            due = d.get("due_date", "")
            status = d.get("status", "")
            if status in ("delivered", "accepted"):
                on_track += 1
            elif due and due < now.date().isoformat() and status not in ("delivered", "accepted"):
                overdue += 1
            else:
                on_track += 1

        overdue_actions = sum(
            1 for a in action_items
            if a.get("status") == "open" and a.get("due_date") and a["due_date"] < now.date().isoformat()
        )

        total = len(deliverables)
        score = 100.0
        if total > 0:
            score = (on_track / total) * 100
        score = max(0, score - overdue * 10 - overdue_actions * 5)

        return EngagementHealth(
            score=round(max(0, min(100, score)), 1),
            deliverables_on_track=on_track,
            deliverables_overdue=overdue,
            deliverables_total=total,
            action_items_overdue=overdue_actions,
            phase_distribution=phase_dist,
        )

    def _compute_risk_posture(self, risks) -> RiskPosture:
        open_risks = [r for r in risks if r.get("status") == "open"]
        critical = sum(1 for r in open_risks if r.get("probability", 0) * r.get("impact", 0) >= 15)
        weighted = sum(r.get("probability", 0) * r.get("impact", 0) for r in open_risks)
        max_possible = len(open_risks) * 25 if open_risks else 1

        score = 100 - (weighted / max_possible) * 100 if max_possible > 0 else 100
        score = max(0, score - critical * 15)

        return RiskPosture(
            score=round(max(0, min(100, score)), 1),
            total_risks=len(risks),
            open_risks=len(open_risks),
            critical_risks=critical,
            weighted_severity=round(weighted, 1),
            trend="stable",
        )

    def _compute_relationship_health(self, interactions, memory, now) -> RelationshipHealth:
        stakeholders = memory.get("key_stakeholders", []) if memory else []

        days_since = 999
        if interactions:
            latest = max(interactions, key=lambda i: i.get("date", ""))
            try:
                last_date = datetime.fromisoformat(latest["date"].replace("Z", "+00:00"))
                days_since = (now - last_date).days
            except (ValueError, KeyError):
                pass

        gaps = max(0, len(stakeholders) - len(interactions)) if stakeholders else 0

        score = 100.0
        if days_since > 30:
            score -= 40
        elif days_since > 14:
            score -= 20
        elif days_since > 7:
            score -= 10

        if len(stakeholders) > 0 and len(interactions) == 0:
            score -= 30

        return RelationshipHealth(
            score=round(max(0, min(100, score)), 1),
            days_since_last_interaction=days_since,
            stakeholders_with_gaps=gaps,
            total_stakeholders=len(stakeholders),
        )

    def _score_to_grade(self, score: float) -> str:
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        return "F"

    async def _query(self, client_id: str, container: str) -> list:
        try:
            repo = await self._manager.get_client_repo(client_id, container)
            return await repo.query("SELECT * FROM c", [])
        except Exception:
            return []

    async def _get_memory(self, client_id: str) -> dict:
        try:
            repo = await self._manager.get_client_repo(client_id, "memories")
            return await repo.get(client_id, client_id) or {}
        except Exception:
            return {}
