# backend/app/services/analysis.py
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.models.analysis import (
    AnalysisResult, ExtractedStakeholder, ExtractedActionItem,
    ExtractedRisk, ExtractedDate,
)
from app.models.source import ParsedDocument
from app.telemetry import track_event

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are a consulting intelligence analyst. Analyze the following document and extract structured information.

Respond ONLY with valid JSON matching this schema:
{
  "doc_type": "meeting_notes|contract|proposal|status_report|email|presentation|spreadsheet|memo|other",
  "analysis_summary": "2-3 sentence summary of the document",
  "extracted_stakeholders": [{"name": "...", "title": "...", "email": "...", "organization": "...", "confidence": 0.0-1.0}],
  "extracted_actions": [{"description": "...", "owner": "...", "due_date": "YYYY-MM-DD or null", "priority": "high|medium|low", "source_section": "..."}],
  "extracted_dates": [{"date": "YYYY-MM-DD", "description": "...", "date_type": "deadline|meeting|milestone|other"}],
  "extracted_risks": [{"description": "...", "severity": "high|medium|low", "category": "technical|commercial|operational|timeline", "source_section": "..."}],
  "engagement_references": ["project or engagement names mentioned"],
  "key_topics": ["main themes or topics discussed"]
}

Rules:
- Extract stakeholder names from signatures, headers, attendee lists, CC lines, org charts
- Identify action items from bullet points, "TODO", "Action:", "Next steps" patterns
- Detect risks from "risk", "concern", "issue", "blocker" language
- Classify the document type based on structure and content
- Set confidence scores for stakeholders (1.0 = explicitly named with title, 0.5 = mentioned by name only)
- If a field has no data, use an empty list

DOCUMENT TEXT:
"""


class AnalysisService:
    def __init__(self):
        self._client = None

    async def initialize(self):
        settings = get_settings()
        if settings.LOCAL_MODE and not settings.AZURE_OPENAI_ENDPOINT:
            logger.info("AnalysisService: LOCAL_MODE without endpoint, using mock")
            return

        from openai import AsyncAzureOpenAI
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version=settings.AZURE_OPENAI_API_VERSION,
        )

    async def analyze_document(
        self, parsed: ParsedDocument, client_name: str
    ) -> AnalysisResult:
        import time
        start = time.time()

        text = "\n\n".join(
            (f"## {s.title}\n{s.text}" if s.title else s.text)
            for s in parsed.sections
        )
        # Truncate to ~12K tokens (~48K chars as rough estimate)
        text = text[:48000]

        if self._client is None:
            return self._mock_analysis(parsed.file_path, client_name, text)

        settings = get_settings()
        try:
            response = await self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": ANALYSIS_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content or "{}"
            data = json.loads(content)

            result = AnalysisResult(
                file_path=parsed.file_path,
                client_name=client_name,
                doc_type=data.get("doc_type", "unknown"),
                analysis_summary=data.get("analysis_summary", ""),
                extracted_stakeholders=[
                    ExtractedStakeholder(**s) for s in data.get("extracted_stakeholders", [])
                ],
                extracted_actions=[
                    ExtractedActionItem(**a) for a in data.get("extracted_actions", [])
                ],
                extracted_dates=[
                    ExtractedDate(**d) for d in data.get("extracted_dates", [])
                ],
                extracted_risks=[
                    ExtractedRisk(**r) for r in data.get("extracted_risks", [])
                ],
                engagement_references=data.get("engagement_references", []),
                key_topics=data.get("key_topics", []),
            )

            duration_ms = int((time.time() - start) * 1000)
            track_event("document.analyzed", {
                "file_path": parsed.file_path,
                "doc_type": result.doc_type,
                "stakeholder_count": len(result.extracted_stakeholders),
                "action_count": len(result.extracted_actions),
                "risk_count": len(result.extracted_risks),
                "duration_ms": duration_ms,
            })

            return result

        except Exception as e:
            logger.error("Analysis failed for %s: %s", parsed.file_path, e)
            return AnalysisResult(
                file_path=parsed.file_path,
                client_name=client_name,
                analysis_summary=f"Analysis failed: {e}",
            )

    def _mock_analysis(self, file_path: str, client_name: str, text: str) -> AnalysisResult:
        return AnalysisResult(
            file_path=file_path,
            client_name=client_name,
            doc_type="unknown",
            analysis_summary="[LOCAL_MODE] Mock analysis — configure Azure OpenAI for real extraction.",
            key_topics=["mock"],
        )

    async def close(self):
        if self._client:
            await self._client.close()


async def merge_analysis_into_memory(result: AnalysisResult, memory_repo) -> dict:
    """Auto-merge extracted entities into client memory."""
    client_id = result.client_name.lower().replace(" ", "-")
    memory = await memory_repo.get(client_id, client_id)
    if memory is None:
        memory = {"id": client_id, "client_name": result.client_name}

    # Merge stakeholders (deduplicate by name)
    existing_names = {s.get("name", "").lower() for s in memory.get("key_stakeholders", [])}
    for s in result.extracted_stakeholders:
        if s.name.lower() not in existing_names:
            memory.setdefault("key_stakeholders", []).append(s.model_dump())
            existing_names.add(s.name.lower())

    # Merge action items
    existing_actions = {a.get("description", "").lower() for a in memory.get("open_action_items", [])}
    for a in result.extracted_actions:
        if a.description.lower() not in existing_actions:
            memory.setdefault("open_action_items", []).append({
                "description": a.description,
                "owner": a.owner,
                "due_date": a.due_date,
                "completed": False,
            })
            existing_actions.add(a.description.lower())

    # Merge engagement references
    existing_eng = set(memory.get("active_engagements", []))
    for eng in result.engagement_references:
        if eng not in existing_eng:
            memory.setdefault("active_engagements", []).append(eng)
            existing_eng.add(eng)

    # Merge pain points from risks
    existing_pains = set(memory.get("pain_points", []))
    for r in result.extracted_risks:
        if r.description not in existing_pains:
            memory.setdefault("pain_points", []).append(r.description)
            existing_pains.add(r.description)

    # Track source
    if result.file_path not in memory.get("sources", []):
        memory.setdefault("sources", []).append(result.file_path)

    memory["last_updated"] = datetime.now(timezone.utc).isoformat()
    await memory_repo.upsert(memory)
    return memory
