from app.dependencies import get_client_analysis_repo, get_client_memory_repo


async def generate_insights(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    insight_types = arguments.get("insight_types") or ["memory", "analyses", "risks", "action_items"]
    max_insights = min(int(arguments.get("max_insights", 10)), 50)

    if not client_name:
        raise ValueError("client_name is required")

    result: dict = {"client_name": client_name}

    if "memory" in insight_types:
        try:
            mem_repo = await get_client_memory_repo(client_name)
            if mem_repo:
                client_id = client_name.lower().replace(" ", "-")
                memory = await mem_repo.get(client_id, client_id)
                result["memory"] = memory
        except Exception:
            result["memory"] = None

    if "analyses" in insight_types:
        try:
            analysis_repo = await get_client_analysis_repo(client_name)
            if analysis_repo:
                analyses = await analysis_repo.query("SELECT * FROM c", [])
                result["recent_analyses"] = [
                    {
                        "file_path": a.get("file_path", ""),
                        "doc_type": a.get("doc_type", ""),
                        "summary": a.get("analysis_summary", "")[:300],
                        "analyzed_at": a.get("analyzed_at", ""),
                    }
                    for a in analyses[:max_insights]
                ]
        except Exception:
            result["recent_analyses"] = []

    if "risks" in insight_types:
        try:
            from app.dependencies import get_cosmos_manager
            manager = get_cosmos_manager()
            if manager:
                client_id = client_name.lower().replace(" ", "-")
                risks_repo = await manager.get_client_repo(client_id, "risks")
                risks = await risks_repo.query("SELECT * FROM c", [])
                result["risks"] = risks[:max_insights]
        except Exception:
            result["risks"] = []

    if "action_items" in insight_types:
        try:
            from app.dependencies import get_client_action_items_repo
            ai_repo = await get_client_action_items_repo(client_name)
            if ai_repo:
                items = await ai_repo.query("SELECT * FROM c WHERE c.status = 'open'", [])
                result["open_action_items"] = items[:max_insights]
        except Exception:
            result["open_action_items"] = []

    return result
