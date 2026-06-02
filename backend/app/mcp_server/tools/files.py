from app.dependencies import get_client_doc_index_repo


async def list_indexed_files(arguments: dict) -> dict:
    client_name = arguments.get("client_name", "")
    page = max(1, int(arguments.get("page", 1)))
    page_size = min(int(arguments.get("page_size", 20)), 100)

    if not client_name:
        raise ValueError("client_name is required")

    repo = await get_client_doc_index_repo(client_name)
    if repo is None:
        raise RuntimeError("Document index service not initialized")

    docs = await repo.query("SELECT c.file_path, c.last_indexed FROM c", [])

    offset = (page - 1) * page_size
    page_docs = docs[offset : offset + page_size]

    return {
        "client_name": client_name,
        "files": page_docs,
        "total": len(docs),
        "page": page,
        "page_size": page_size,
        "pages": max(1, (len(docs) + page_size - 1) // page_size),
    }
