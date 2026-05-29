import asyncio
import json
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 2000


class ContextInjector:
    def __init__(self, cosmos_manager):
        self._manager = cosmos_manager
        self._enc = None

    def _get_encoder(self):
        if self._enc is None:
            try:
                import tiktoken
                self._enc = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                self._enc = None
        return self._enc

    def _count_tokens(self, text: str) -> int:
        enc = self._get_encoder()
        if enc:
            return len(enc.encode(text))
        return len(text) // 4

    async def build_context_block(self, client_name: str) -> str:
        if not self._manager:
            return ""

        client_id = client_name.lower().replace(" ", "-")

        try:
            memory, interactions, risks, action_items = await asyncio.gather(
                self._fetch_memory(client_id),
                self._fetch_recent_interactions(client_id),
                self._fetch_active_risks(client_id),
                self._fetch_overdue_actions(client_id),
            )
        except Exception as e:
            logger.warning("Context injection failed for %s: %s", client_name, e)
            return ""

        block = self._format_context(client_name, memory, interactions, risks, action_items)

        if self._count_tokens(block) > TOKEN_BUDGET:
            block = self._truncate(block)

        return block

    async def _fetch_memory(self, client_id: str) -> dict:
        try:
            repo = await self._manager.get_client_repo(client_id, "memories")
            memory = await repo.get(client_id, client_id)
            return memory or {}
        except Exception:
            return {}

    async def _fetch_recent_interactions(self, client_id: str) -> list:
        try:
            repo = await self._manager.get_client_repo(client_id, "interactions")
            items = await repo.query("SELECT * FROM c ORDER BY c.date DESC", [])
            return items[:5]
        except Exception:
            return []

    async def _fetch_active_risks(self, client_id: str) -> list:
        try:
            repo = await self._manager.get_client_repo(client_id, "risks")
            items = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
            return sorted(
                items,
                key=lambda r: r.get("probability", 0) * r.get("impact", 0),
                reverse=True,
            )[:10]
        except Exception:
            return []

    async def _fetch_overdue_actions(self, client_id: str) -> list:
        try:
            repo = await self._manager.get_client_repo(client_id, "action_items")
            items = await repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).date().isoformat()
            return [a for a in items if a.get("due_date") and a["due_date"] < now]
        except Exception:
            return []

    def _format_context(self, client_name, memory, interactions, risks, overdue_actions) -> str:
        parts = [f"=== CLIENT CONTEXT: {client_name} ==="]

        if memory:
            industry = memory.get("industry", "Unknown")
            priorities = memory.get("strategic_priorities", [])
            pains = memory.get("pain_points", [])
            parts.append(f"Industry: {industry}")
            if priorities:
                parts.append(f"Priorities: {', '.join(priorities[:5])}")
            if pains:
                parts.append(f"Pain points: {', '.join(pains[:5])}")

        if interactions:
            parts.append(f"\nRECENT INTERACTIONS ({len(interactions)}):")
            for i in interactions:
                parts.append(f"- [{i.get('type', '?')}] {i.get('date', '?')}: {i.get('summary', '')[:100]}")

        if risks:
            parts.append(f"\nACTIVE RISKS ({len(risks)}):")
            for r in risks:
                sev = r.get("probability", 0) * r.get("impact", 0)
                parts.append(f"- [Sev:{sev}] {r.get('description', '')[:100]}")

        if overdue_actions:
            parts.append(f"\nOVERDUE ACTION ITEMS ({len(overdue_actions)}):")
            for a in overdue_actions:
                parts.append(f"- {a.get('description', '')[:80]} (due: {a.get('due_date', '?')}, owner: {a.get('owner', '?')})")

        parts.append("===")
        return "\n".join(parts)

    def _truncate(self, block: str) -> str:
        lines = block.split("\n")
        result = []
        for line in lines:
            result.append(line)
            if self._count_tokens("\n".join(result)) > TOKEN_BUDGET:
                result.pop()
                break
        result.append("=== (context truncated) ===")
        return "\n".join(result)
