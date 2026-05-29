"""One-time script to create the Azure AI Search index."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


async def main():
    from app.config import get_settings
    settings = get_settings()

    if settings.LOCAL_MODE:
        print("LOCAL_MODE is enabled — no search index to create.")
        return

    from app.services.search import SearchService
    service = SearchService()
    await service.initialize()
    await service.ensure_index()
    print(f"Search index '{settings.AZURE_SEARCH_INDEX_NAME}' created/updated successfully.")
    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
