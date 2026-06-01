# backend/app/agent/web_search_plugin.py
import json
import logging
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class WebSearchPlugin:
    def __init__(self, settings):
        self._tavily_key = getattr(settings, "TAVILY_API_KEY", "")

    @kernel_function(
        name="web_search",
        description=(
            "Search the web for current information, news, market trends, or topics not covered "
            "in client documents. Returns titles, URLs, and content excerpts. "
            "Use for industry research, competitor analysis, or recent events."
        ),
    )
    async def web_search(self, query: str, max_results: int = 5) -> str:
        if self._tavily_key:
            return await self._tavily_search(query, max_results)
        return await self._ddg_search(query, max_results)

    @kernel_function(
        name="fetch_url",
        description=(
            "Fetch and extract the main text content from a URL. "
            "Use when the user pastes a link or when web_search returns a URL worth reading in full."
        ),
    )
    async def fetch_url(self, url: str) -> str:
        try:
            import trafilatura
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return json.dumps({"error": "Could not fetch URL"})
            text = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if not text:
                return json.dumps({"error": "No extractable content found"})
            return json.dumps({"url": url, "content": text[:4000]})
        except Exception as e:
            logger.warning("fetch_url failed for %s: %s", url, e)
            return json.dumps({"error": str(e)})

    async def _tavily_search(self, query: str, max_results: int) -> str:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=self._tavily_key)
            response = client.search(query=query, max_results=max_results, include_raw_content=False)
            results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:400],
                }
                for r in response.get("results", [])
            ]
            return json.dumps(results, indent=2)
        except Exception as e:
            logger.warning("Tavily search failed: %s — falling back to DuckDuckGo", e)
            return await self._ddg_search(query, max_results)

    async def _ddg_search(self, query: str, max_results: int) -> str:
        try:
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddg:
                for r in ddg.text(query, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")[:400],
                    })
            return json.dumps(results, indent=2)
        except Exception as e:
            logger.warning("DuckDuckGo search failed: %s", e)
            return json.dumps({"error": str(e)})
