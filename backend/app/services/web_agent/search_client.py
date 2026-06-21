"""
DuckDuckGo search client.

Wraps the `duckduckgo_search` package with retry/backoff (DDGS rate-limits
aggressively) and normalizes results into a simple dataclass so the rest
of the pipeline doesn't depend on the third-party library's response shape.
"""

from __future__ import annotations

from dataclasses import dataclass

from ddgs import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("search_client")


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str


class SearchUnavailableError(Exception):
    """Raised when DuckDuckGo search fails after all retries."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1.5, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def _raw_search(query: str, max_results: int, region: str, safesearch: str) -> list[dict]:
    with DDGS() as ddgs:
        return list(
            ddgs.text(
                query,
                region=region,
                safesearch=safesearch,
                max_results=max_results,
            )
        )


def search_web(query: str, max_results: int | None = None) -> list[SearchHit]:
    """Run a DuckDuckGo text search and return normalized hits.

    Returns an empty list (never raises to the caller) on total failure --
    the pipeline should degrade gracefully to KB-only results rather than
    500 the whole request because search is rate-limited.
    """
    settings = get_settings()
    max_results = max_results or settings.search_max_results

    try:
        raw = _raw_search(
            query=query,
            max_results=max_results,
            region=settings.search_region,
            safesearch=settings.search_safesearch,
        )
    except Exception as e:
        log.error(f"DuckDuckGo search failed for query '{query}': {e}")
        return []

    hits = []
    for item in raw:
        url = item.get("href") or item.get("url")
        title = item.get("title", "").strip()
        snippet = item.get("body", "").strip()
        if not url or not title:
            continue
        hits.append(SearchHit(title=title, url=url, snippet=snippet))

    log.info(f"Search '{query}' -> {len(hits)} hits")
    return hits
