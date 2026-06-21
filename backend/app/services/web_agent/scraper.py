"""
Async web page scraper.

Fetches pages concurrently (bounded by a semaphore) and extracts clean
body text via trafilatura, which strips nav bars, ads, footers, and
cookie banners far better than naive BeautifulSoup text-dumping.

Failures (timeouts, 403s, non-HTML content, paywalls) are isolated per-URL
so one bad page never kills the whole batch.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import httpx
import trafilatura

from app.core.config import get_settings
from app.core.logging import get_logger
from app.utils.text_processing import clean_text
from app.utils.url_utils import get_domain

log = get_logger("scraper")


@dataclass
class ScrapedPage:
    url: str
    domain: str
    title: str
    text: str
    success: bool
    error: str | None = None


async def _fetch_one(client: httpx.AsyncClient, url: str, title_hint: str) -> ScrapedPage:
    settings = get_settings()
    domain = get_domain(url)
    try:
        resp = await client.get(url, timeout=settings.scrape_timeout_seconds, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type and "pdf" not in content_type:
            return ScrapedPage(url, domain, title_hint, "", False, f"unsupported content-type: {content_type}")

        if "pdf" in content_type:
            # Skip binary PDF parsing in the live-scrape path; KB ingestion
            # pipeline handles PDFs separately and deliberately.
            return ScrapedPage(url, domain, title_hint, "", False, "pdf-skip")

        extracted = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        if not extracted:
            return ScrapedPage(url, domain, title_hint, "", False, "no extractable text")

        text = clean_text(extracted)[: settings.scrape_max_chars_per_page]
        if len(text) < settings.scrape_min_text_chars:
            return ScrapedPage(url, domain, title_hint, text, False, "text too short")

        return ScrapedPage(url, domain, title_hint, text, True, None)

    except httpx.HTTPStatusError as e:
        return ScrapedPage(url, domain, title_hint, "", False, f"HTTP {e.response.status_code}")
    except Exception as e:
        return ScrapedPage(url, domain, title_hint, "", False, str(e)[:200])


async def scrape_urls(url_title_pairs: list[tuple[str, str]]) -> list[ScrapedPage]:
    """Scrape multiple URLs concurrently, bounded by settings.scrape_max_concurrent."""
    settings = get_settings()
    semaphore = asyncio.Semaphore(settings.scrape_max_concurrent)
    headers = {"User-Agent": settings.user_agent}

    async def bounded_fetch(client: httpx.AsyncClient, url: str, title: str) -> ScrapedPage:
        async with semaphore:
            return await _fetch_one(client, url, title)

    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [bounded_fetch(client, url, title) for url, title in url_title_pairs]
        results = await asyncio.gather(*tasks)

    ok = sum(1 for r in results if r.success)
    log.info(f"Scraped {ok}/{len(results)} pages successfully")
    return list(results)
