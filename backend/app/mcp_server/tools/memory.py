from datetime import datetime, timezone

from app.dependencies import get_client_memory_repo


async def read_client_memory(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    fields = arguments.get("fields")

    if not client_name:
        raise ValueError("client_name is required")

    repo = await get_client_memory_repo(client_name)
    if repo is None:
        raise RuntimeError("Memory service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    memory = await repo.get(client_id, client_id)
    if memory is None:
        return {"client_name": client_name, "memory": None, "found": False}

    if fields:
        memory = {k: v for k, v in memory.items() if k in fields}

    return {"client_name": client_name, "memory": memory, "found": True}


async def write_client_memory(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    field = arguments.get("field", "")
    value = arguments.get("value")
    overwrite = bool(arguments.get("overwrite", False))

    if not client_name:
        raise ValueError("client_name is required")
    if not field:
        raise ValueError("field is required")
    if value is None:
        raise ValueError("value is required")

    repo = await get_client_memory_repo(client_name)
    if repo is None:
        raise RuntimeError("Memory service not initialized")

    client_id = client_name.lower().replace(" ", "-")
    memory = await repo.get(client_id, client_id) or {"id": client_id, "client_name": client_name}

    if not overwrite and field in memory:
        existing = memory[field]
        if isinstance(existing, list) and isinstance(value, list):
            memory[field] = existing + value
        else:
            return {
                "status": "skipped",
                "field": field,
                "reason": "Field exists and overwrite=false",
            }
    else:
        memory[field] = value

    memory["last_updated"] = datetime.now(timezone.utc).isoformat()
    await repo.upsert(memory)
    return {"status": "updated", "client_name": client_name, "field": field}
