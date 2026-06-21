"""
Web Research Agent orchestrator.

This is the "Claude/ChatGPT-style search agent" the user asked for, built
entirely from local/free components:

    query/topic
        -> DuckDuckGo search           (search_client.py)
        -> concurrent page scraping    (scraper.py)
        -> sentence-level relevance    (sentence_ranker.py)
        -> keyword marking             (keyword_extractor.py)
        -> ComponentTopicResult        (models/schemas.py)

Every claim in the output is a verbatim sentence from a real, linked
source -- nothing is generated/hallucinated, satisfying the "deliver an
output along with the links through which they extracted the information"
requirement without needing an LLM API.
"""

from __future__ import annotations

import time

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import CitedSnippet, ComponentTopicResult, KeywordHit, ResearchSource, SourceType
from app.services.web_agent import cache
from app.services.web_agent.keyword_extractor import extract_keywords
from app.services.web_agent.scraper import scrape_urls
from app.services.web_agent.search_client import search_web
from app.services.web_agent.sentence_ranker import build_extractive_snippets_for_page
from app.utils.url_utils import make_id

log = get_logger("web_research_agent")


async def research_topic(topic: str, max_results: int | None = None) -> ComponentTopicResult:
    """
    Run the full search -> scrape -> rank -> keyword pipeline for a single
    research topic (e.g. "Zero-drift / chopper op-amp") and return a
    structured, citable result block.
    """
    settings = get_settings()
    max_results = max_results or settings.search_max_results

    cached = cache.get_cached(topic)
    if cached:
        log.info(f"Cache hit for topic '{topic}'")
        return ComponentTopicResult.model_validate(cached)

    # Augment the bare topic with a couple of EE-context hint terms so
    # search returns datasheets/app-notes rather than generic dictionary
    # definitions (e.g. "zero-drift op-amp" alone can return marketing fluff).
    search_query = f"{topic} {settings.component_hint_terms[0]} {settings.component_hint_terms[1]}"

    hits = search_web(search_query, max_results=max_results)
    if not hits:
        log.warning(f"No search hits for topic '{topic}'")
        return ComponentTopicResult(topic=topic, keywords=[], extractive_summary=[], sources=[])

    scraped_pages = await scrape_urls([(h.url, h.title) for h in hits])

    sources: list[ResearchSource] = []
    snippets: list[CitedSnippet] = []
    successful_page_texts: list[str] = []

    for page in scraped_pages:
        if not page.success:
            continue

        source_id = make_id("web", page.url)
        ranked = build_extractive_snippets_for_page(page.text, topic)
        if not ranked:
            continue  # page scraped fine but had nothing relevant -> drop it

        sources.append(
            ResearchSource(
                id=source_id,
                title=page.title or page.domain,
                source_type=SourceType.WEB,
                url=page.url,
                domain=page.domain,
                fetched_at=None,
                snippet_count=len(ranked),
            )
        )
        for sentence, score in ranked:
            snippets.append(CitedSnippet(text=sentence, relevance_score=score, source_id=source_id))
        successful_page_texts.append(page.text)

    # Sort all snippets across sources by relevance, globally, so the best
    # evidence surfaces first regardless of which page it came from.
    snippets.sort(key=lambda s: s.relevance_score, reverse=True)

    # Cap number of distinct sources shown to keep output readable.
    keep_source_ids = {s.id for s in sources[: settings.max_sources_in_summary]}
    sources = [s for s in sources if s.id in keep_source_ids]
    snippets = [sn for sn in snippets if sn.source_id in keep_source_ids]

    # Keywords: extract from the concatenation of top scraped text (cheap,
    # representative) rather than every page individually.
    combined_text = " ".join(successful_page_texts)[:6000]
    kw_hits = extract_keywords(combined_text or topic, top_n=settings.keybert_top_n)
    keywords = [KeywordHit(keyword=k.keyword, score=k.score) for k in kw_hits]

    result = ComponentTopicResult(
        topic=topic,
        keywords=keywords,
        extractive_summary=snippets,
        sources=sources,
    )

    cache.set_cached(topic, result.model_dump(mode="json"))
    return result


async def research_topics(topics: list[str], max_results: int | None = None) -> list[ComponentTopicResult]:
    """Research multiple topics. Sequential by design (not parallel) to stay
    polite to DuckDuckGo's rate limits -- search_client already retries with
    backoff, but hammering it concurrently across topics triggers blocks."""
    results = []
    for topic in topics:
        start = time.perf_counter()
        try:
            res = await research_topic(topic, max_results=max_results)
        except Exception as e:
            log.error(f"Topic research failed for '{topic}': {e}")
            res = ComponentTopicResult(topic=topic, keywords=[], extractive_summary=[], sources=[])
        elapsed = (time.perf_counter() - start) * 1000
        log.info(f"Topic '{topic}' researched in {elapsed:.0f}ms "
                  f"({len(res.sources)} sources, {len(res.extractive_summary)} snippets)")
        results.append(res)
    return results
