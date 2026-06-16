# backend/app/api/inbox_search.py
"""
POST /api/search — AI-powered inbox email search.

Pipeline:
  1. EmailQueryAnalyzer expands the query and extracts filters via LLM.
  2. search_outlook_inbox searches win32com (primary) or Graph API (fallback).
  3. Semantic re-ranking via embedding cosine similarity.
  4. Client attribution from comm configs stored in Cosmos.
  5. LLM summarization of top results.
"""
import logging
import time
from typing import Optional

import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/search", tags=["inbox-search"])
logger = logging.getLogger(__name__)

_CLIENT_CACHE_TTL = 300  # seconds
_client_config_cache: dict = {}
_client_config_cache_at: float = 0.0


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class EmailSearchRequest(BaseModel):
    query: str
    days: int = 90
    conversation_history: list[dict] = []


class InboxSearchResult(BaseModel):
    id: str
    subject: str
    sender: str
    sender_name: str
    recipients: list[str]
    body_preview: str
    received_at: Optional[str]
    folder: str
    account: str
    has_attachment: bool
    attachment_names: list[str]
    client_name: Optional[str]
    client_path: Optional[str]
    relevance_score: float


class EmailSearchResponse(BaseModel):
    results: list[InboxSearchResult]
    summary: str
    expanded_queries: list[str]
    filters_applied: dict
    total_found: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)


async def _get_all_client_configs(cosmos_manager) -> list[dict]:
    """Load communication configs for all clients from Cosmos, cached for 5 min."""
    global _client_config_cache, _client_config_cache_at
    now = time.time()
    if now - _client_config_cache_at < _CLIENT_CACHE_TTL and _client_config_cache:
        return list(_client_config_cache.values())

    configs: list[dict] = []
    try:
        # Access the raw CosmosClient directly — do NOT use `async with` here because
        # CosmosClient.__aexit__ calls close(), which would shut down the shared client.
        raw_client = getattr(cosmos_manager, '_client', None)
        if raw_client is None:
            return []
        dbs = [db async for db in raw_client.list_databases()]
        for db in dbs:
            if not db["id"].startswith("client_"):
                continue
            client_id = db["id"][len("client_"):]
            try:
                db_client = raw_client.get_database_client(db["id"])
                container = db_client.get_container_client("communication_config")
                items = [i async for i in container.read_all_items()]
                if items:
                    cfg = items[0]
                    configs.append({
                        "client_name": cfg.get("client_name", client_id),
                        "client_id": client_id,
                        "domains": [d.lower() for d in (cfg.get("domains") or [])],
                        "contacts": [c.lower() for c in (cfg.get("contacts") or [])],
                    })
            except Exception:
                pass
    except Exception as e:
        logger.debug("Could not load client configs: %s", e)

    _client_config_cache = {c["client_id"]: c for c in configs}
    _client_config_cache_at = now
    return configs


def _attribute_email(email: dict, configs: list[dict]) -> tuple[Optional[str], Optional[str]]:
    sender = (email.get("sender") or "").lower()
    for cfg in configs:
        for domain in cfg["domains"]:
            d = domain.lstrip("@")
            if d and d in sender:
                return cfg["client_name"], f"/clients/{cfg['client_id']}/communications"
        for contact in cfg["contacts"]:
            if contact and contact == sender:
                return cfg["client_name"], f"/clients/{cfg['client_id']}/communications"
    return None, None


async def _summarize(query: str, results: list[dict], kernel) -> str:
    """Generate a 2-3 sentence summary of the top search results via the LLM."""
    if not results or kernel is None:
        return ""
    try:
        from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
        from semantic_kernel.connectors.ai.open_ai import AzureChatPromptExecutionSettings
        from semantic_kernel.contents import ChatHistory

        from app.prompts.loader import load_prompt

        template = load_prompt("email_search_summarize_prompt.txt")
        top = results[:10]
        formatted = "\n".join(
            f"- From: {r.get('sender_name') or r.get('sender')} "
            f"| Subject: {r.get('subject')} "
            f"| Date: {(r.get('received_at') or '')[:10]} "
            f"| Preview: {r.get('body_preview', '')[:120]}"
            for r in top
        )
        prompt = (
            template
            .replace("{query}", query)
            .replace("{count}", str(len(results)))
            .replace("{results}", formatted)
        )

        chat = ChatHistory()
        chat.add_user_message(prompt)
        settings = AzureChatPromptExecutionSettings(
            service_id="chat",
            max_tokens=256,
            temperature=0.3,
        )
        chat_service = kernel.get_service(type=ChatCompletionClientBase)
        resp = await chat_service.get_chat_message_content(chat, settings=settings)
        return str(resp).strip()
    except Exception as e:
        logger.warning("Summarization failed: %s", e)
        return ""


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=EmailSearchResponse)
async def search_emails(request: EmailSearchRequest) -> EmailSearchResponse:
    """Search the local Outlook inbox using AI-expanded queries.

    Steps:
    1. Analyze query with LLM (expand + extract filters).
    2. Search Outlook via win32com or Graph API fallback.
    3. Semantic re-rank via embedding cosine similarity.
    4. Attribute emails to known clients via comm configs.
    5. Summarize top results with LLM.
    """
    from app.dependencies import get_cosmos_manager, get_embedding_service, get_planner

    # Resolve services from module-level singletons
    planner = get_planner()
    kernel = planner._kernel if planner is not None else None
    embedding_service = get_embedding_service()
    cosmos_manager = get_cosmos_manager()

    # GraphAPIService — retrieve from CommunicationAccess stored in _communication_access
    from app.dependencies import get_communication_access
    comm_access = get_communication_access()
    graph_service = comm_access._graph if comm_access is not None else None

    # 1. Analyze query
    from app.agent.email_query_analyzer import EmailQueryAnalyzer
    analyzer = EmailQueryAnalyzer(kernel)
    analysis = await analyzer.analyze(request.query, request.conversation_history)
    expanded_queries: list[str] = analysis.get("expanded_queries") or [request.query]
    filters: dict = analysis.get("filters") or {}

    # 2. Search Outlook
    from app.services.outlook_inbox_search import search_outlook_inbox
    raw_results = await search_outlook_inbox(
        queries=expanded_queries,
        filters=filters,
        days=request.days,
        graph_service=graph_service,
    )

    # 3. Semantic re-ranking
    if raw_results and embedding_service is not None:
        try:
            query_vec: list[float] = (
                await embedding_service.embed_texts([request.query])
            )[0]
            texts = [
                f"{r.get('subject', '')} {r.get('sender_name', '')} {r.get('body_preview', '')}"
                for r in raw_results
            ]
            result_vecs: list[list[float]] = await embedding_service.embed_texts(texts)
            for i, r in enumerate(raw_results):
                r["_score"] = _cosine(query_vec, result_vecs[i])
            raw_results.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
        except Exception as e:
            logger.warning("Re-ranking failed, using original order: %s", e)

    # 4. Client attribution
    if cosmos_manager is not None:
        try:
            configs = await _get_all_client_configs(cosmos_manager)
            for r in raw_results:
                name, path = _attribute_email(r, configs)
                r["client_name"] = name
                r["client_path"] = path
        except Exception as e:
            logger.debug("Attribution skipped: %s", e)

    # Cap at 50 results
    raw_results = raw_results[:50]

    # 5. Summarize
    summary = await _summarize(request.query, raw_results, kernel)

    results = [
        InboxSearchResult(
            id=r["id"],
            subject=r.get("subject", ""),
            sender=r.get("sender", ""),
            sender_name=r.get("sender_name", ""),
            recipients=r.get("recipients", []),
            body_preview=r.get("body_preview", ""),
            received_at=r.get("received_at"),
            folder=r.get("folder", ""),
            account=r.get("account", ""),
            has_attachment=r.get("has_attachment", False),
            attachment_names=r.get("attachment_names", []),
            client_name=r.get("client_name"),
            client_path=r.get("client_path"),
            relevance_score=round(r.get("_score", 0.0), 4),
        )
        for r in raw_results
    ]

    return EmailSearchResponse(
        results=results,
        summary=summary,
        expanded_queries=expanded_queries,
        filters_applied={k: v for k, v in filters.items() if v is not None},
        total_found=len(results),
    )
