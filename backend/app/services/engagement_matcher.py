import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 0.6


class EngagementMatcher:
    def __init__(self, cosmos_manager):
        self._manager = cosmos_manager

    async def match(self, references: list[str], client_id: str) -> list[dict]:
        """Fuzzy-match text references to actual Engagement records."""
        if not references:
            return []

        try:
            repo = await self._manager.get_client_repo(client_id, "engagements")
            engagements = await repo.query("SELECT * FROM c", [])
        except Exception as e:
            logger.warning("Failed to load engagements for matching: %s", e)
            return []

        if not engagements:
            return []

        results = []
        for ref in references:
            best_match = None
            best_score = 0.0

            for eng in engagements:
                name = eng.get("name", "")
                desc = eng.get("description", "")

                name_score = SequenceMatcher(None, ref.lower(), name.lower()).ratio()
                desc_score = SequenceMatcher(None, ref.lower(), desc.lower()[:100]).ratio() * 0.8

                score = max(name_score, desc_score)
                if score > best_score:
                    best_score = score
                    best_match = eng

            if best_match and best_score >= MATCH_THRESHOLD:
                results.append({
                    "reference": ref,
                    "engagement_id": best_match["id"],
                    "engagement_name": best_match.get("name", ""),
                    "confidence": round(best_score, 2),
                })

        return results
