"""
Tests for app.services.web_agent.research_orchestrator with search and
scraping mocked out, so the merge/ranking/citation logic is verified
without depending on live network access (useful in CI/sandboxes where
DuckDuckGo and arbitrary web domains may be unreachable).

NOTE: tests in this file that exercise sentence ranking / keyword
extraction still require the local embedding model (all-MiniLM-L6-v2),
which is downloaded from huggingface.co on first use. They are marked
`requires_model` and will be skipped automatically if that download is
unavailable (e.g. in a network-restricted sandbox) -- on a normal
developer machine with internet access they run fully.
"""

from unittest.mock import patch

import pytest

from app.services.web_agent.research_orchestrator import research_topic
from app.services.web_agent.scraper import ScrapedPage
from app.services.web_agent.search_client import SearchHit


_MODEL_AVAILABLE_CACHE: bool | None = None


def _embedding_model_available() -> bool:
    """Best-effort check: can the shared embedding model actually be loaded?

    A plain GET to huggingface.co is not a reliable signal (e.g. it can
    return 403 from a proxy/WAF while the actual model CDN is still
    unreachable), so this directly attempts the real load path and caches
    the result for the test session.
    """
    global _MODEL_AVAILABLE_CACHE
    if _MODEL_AVAILABLE_CACHE is not None:
        return _MODEL_AVAILABLE_CACHE

    try:
        from app.core.embeddings import get_embedding_model

        get_embedding_model()
        _MODEL_AVAILABLE_CACHE = True
    except Exception:
        _MODEL_AVAILABLE_CACHE = False
    return _MODEL_AVAILABLE_CACHE


requires_model = pytest.mark.skipif(
    not _embedding_model_available(),
    reason="Embedding model requires network access to huggingface.co (unavailable in this environment)",
)


FAKE_PAGE_TEXT = (
    "The ZD-OPX100 is a zero-drift operational amplifier using chopper stabilization "
    "to cancel input offset voltage and flicker noise. This architecture is excellent "
    "for precision current source applications. The device offers 11 nanovolt per "
    "root hertz input voltage noise density at 1 kHz, which is extremely low compared "
    "to conventional operational amplifiers. Unrelated marketing text about discounts "
    "and shipping policies appears here too, mixed into the page body content randomly."
)


@requires_model
@pytest.mark.asyncio
async def test_research_topic_returns_structured_result_from_mocked_pipeline():
    fake_hits = [
        SearchHit(title="Zero Drift Opamp Guide", url="https://example.com/zd-opamp", snippet="..."),
    ]
    fake_scraped = [
        ScrapedPage(
            url="https://example.com/zd-opamp",
            domain="example.com",
            title="Zero Drift Opamp Guide",
            text=FAKE_PAGE_TEXT,
            success=True,
            error=None,
        ),
    ]

    with (
        patch("app.services.web_agent.research_orchestrator.search_web", return_value=fake_hits),
        patch("app.services.web_agent.research_orchestrator.scrape_urls", return_value=fake_scraped),
        patch("app.services.web_agent.research_orchestrator.cache.get_cached", return_value=None),
        patch("app.services.web_agent.research_orchestrator.cache.set_cached", return_value=None),
    ):
        result = await research_topic("Zero-drift / chopper op-amp")

    assert result.topic == "Zero-drift / chopper op-amp"
    assert len(result.sources) == 1
    assert result.sources[0].url is not None
    assert str(result.sources[0].url).startswith("https://example.com")

    # Every snippet must cite a source_id that actually exists in `sources`
    valid_ids = {s.id for s in result.sources}
    for snippet in result.extractive_summary:
        assert snippet.source_id in valid_ids
        assert 0.0 <= snippet.relevance_score <= 1.0


@pytest.mark.asyncio
async def test_research_topic_handles_no_search_results_gracefully():
    with (
        patch("app.services.web_agent.research_orchestrator.search_web", return_value=[]),
        patch("app.services.web_agent.research_orchestrator.cache.get_cached", return_value=None),
    ):
        result = await research_topic("some obscure topic with no hits")

    assert result.sources == []
    assert result.extractive_summary == []


@requires_model
@pytest.mark.asyncio
async def test_research_topic_drops_failed_scrapes():
    fake_hits = [
        SearchHit(title="Dead Link", url="https://example.com/404", snippet="..."),
    ]
    fake_scraped = [
        ScrapedPage(
            url="https://example.com/404", domain="example.com", title="Dead Link",
            text="", success=False, error="HTTP 404",
        ),
    ]
    with (
        patch("app.services.web_agent.research_orchestrator.search_web", return_value=fake_hits),
        patch("app.services.web_agent.research_orchestrator.scrape_urls", return_value=fake_scraped),
        patch("app.services.web_agent.research_orchestrator.cache.get_cached", return_value=None),
    ):
        result = await research_topic("topic with dead link")

    assert result.sources == []
    assert result.extractive_summary == []
