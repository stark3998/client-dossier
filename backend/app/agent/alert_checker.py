import asyncio
import logging
from datetime import datetime, timezone

from app.models.alert import Alert

logger = logging.getLogger(__name__)


class AlertChecker:
    def __init__(self, cosmos_manager, event_bus=None):
        self._manager = cosmos_manager
        self._event_bus = event_bus
        self._task = None

    async def start(self, interval_seconds: int = 900):
        self._task = asyncio.create_task(self._run_loop(interval_seconds))

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _run_loop(self, interval: int):
        while True:
            try:
                await asyncio.sleep(interval)
                await self._check_all_clients()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Alert checker error: %s", e)

    async def _check_all_clients(self):
        try:
            master = self._manager.get_master_repo()
            clients = await master.query("SELECT * FROM c", [])
            for client in clients:
                name = client.get("name") or client.get("client_name") or client.get("id", "")
                if name:
                    alerts = await self.check_client(name)
                    if alerts and self._event_bus:
                        for alert in alerts:
                            from app.models.event import ClientEvent
                            await self._event_bus.publish(ClientEvent(
                                client_name=name,
                                event_type=f"alert_{alert.type}",
                                entity_type=alert.type,
                                entity_id=alert.entity_id or "",
                                summary=alert.title,
                                severity=alert.severity,
                            ))
        except Exception as e:
            logger.warning("Failed to check all clients: %s", e)

    async def check_client(self, client_name: str) -> list[Alert]:
        alerts: list[Alert] = []
        client_id = client_name.lower().replace(" ", "-")
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()

        # Overdue action items
        try:
            repo = await self._manager.get_client_repo(client_id, "action_items")
            items = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
            for item in items:
                if item.get("due_date") and item["due_date"] < today:
                    alerts.append(Alert(
                        type="overdue_action",
                        severity="warning",
                        title=f"Overdue: {item.get('description', '')[:60]}",
                        detail=f"Due {item['due_date']}, owner: {item.get('owner', 'unassigned')}",
                        client_name=client_name,
                        entity_id=item.get("id", ""),
                    ))
        except Exception:
            pass

        # High-severity risks
        try:
            repo = await self._manager.get_client_repo(client_id, "risks")
            risks = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
            for r in risks:
                sev = r.get("probability", 0) * r.get("impact", 0)
                if sev >= 15:
                    alerts.append(Alert(
                        type="high_risk",
                        severity="critical",
                        title=f"Critical risk: {r.get('description', '')[:60]}",
                        detail=f"Severity {sev} (P{r.get('probability')} x I{r.get('impact')})",
                        client_name=client_name,
                        entity_id=r.get("id", ""),
                    ))
        except Exception:
            pass

        # Stale engagements (no status update in 14 days)
        try:
            eng_repo = await self._manager.get_client_repo(client_id, "engagements")
            engagements = await eng_repo.query("SELECT * FROM c WHERE c.status = 'active'", [])
            su_repo = await self._manager.get_client_repo(client_id, "status_updates")
            for eng in engagements:
                updates = await su_repo.query(
                    "SELECT * FROM c WHERE c.engagement_id = @eid ORDER BY c.date DESC",
                    [{"name": "@eid", "value": eng.get("id", "")}],
                )
                if not updates:
                    alerts.append(Alert(
                        type="stale_engagement",
                        severity="info",
                        title=f"No updates: {eng.get('name', '')[:60]}",
                        detail="No status updates recorded for this engagement",
                        client_name=client_name,
                        entity_id=eng.get("id", ""),
                    ))
                else:
                    latest = updates[0].get("date", "")
                    if latest and latest < (now.replace(day=max(1, now.day - 14))).isoformat()[:10]:
                        alerts.append(Alert(
                            type="stale_engagement",
                            severity="warning",
                            title=f"Stale: {eng.get('name', '')[:60]}",
                            detail=f"Last update: {latest}",
                            client_name=client_name,
                            entity_id=eng.get("id", ""),
                        ))
        except Exception:
            pass

        return alerts

    async def generate_briefing(self, client_name: str) -> str:
        alerts = await self.check_client(client_name)
        if not alerts:
            return ""

        parts = [f"Briefing for {client_name}:"]
        overdue = [a for a in alerts if a.type == "overdue_action"]
        risks = [a for a in alerts if a.type == "high_risk"]
        stale = [a for a in alerts if a.type == "stale_engagement"]

        if overdue:
            parts.append(f"- {len(overdue)} overdue action item(s)")
        if risks:
            parts.append(f"- {len(risks)} critical risk(s) need attention")
        if stale:
            parts.append(f"- {len(stale)} engagement(s) with no recent updates")

        return "\n".join(parts)
