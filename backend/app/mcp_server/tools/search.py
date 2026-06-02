import json

from app.dependencies import get_embedding_service, get_search_service


async def search_client_documents(arguments: dict) -> dict:
    query = arguments.get("query", "")
    client_id = arguments.get("client_id")
    top_k = min(int(arguments.get("top_k", 5)), 20)

    search_svc = get_search_service()
    embed_svc = get_embedding_service()
    if search_svc is None or embed_svc is None:
        raise RuntimeError("Search service not initialized")

    filters = f"client_name eq '{client_id}'" if client_id else None
    vector = await embed_svc.embed_query(query)
    candidates = await search_svc.hybrid_search(
        query_text=query,
        query_vector=vector,
        top=top_k * 3,
        filters=filters,
    )
    results = search_svc.rerank(query, candidates, top_k=top_k)
    return {
        "results": [
            {
                "content": r.get("content", ""),
                "file_path": r.get("file_path", ""),
                "file_type": r.get("file_type", ""),
                "section_title": r.get("section_title", ""),
                "page_number": r.get("page_number"),
                "client_name": r.get("client_name", ""),
                "score": round(r.get("score", 0.0), 4),
            }
            for r in results
        ],
        "count": len(results),
        "query": query,
    }
