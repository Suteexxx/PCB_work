"""
Top-level hybrid research pipeline.

This is the single entrypoint the API router calls. It:
  1. Detects research topics/components from the raw user design prompt.
  2. Runs KB search and web research per topic (in parallel where possible).
  3. Merges per-topic results (KB sources + web sources, snippets re-sorted).
  4. Builds a global keyword list across the whole query.
  5. Times each stage for observability (returned in the API response).
"""

from __future__ import annotations

import asyncio
import time

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import ComponentTopicResult, KeywordHit, ResearchResponse, ResearchSource
from app.services.knowledge_base.kb_query_service import research_topics_in_kb
from app.services.knowledge_base.vector_store import kb_document_count
from app.services.web_agent.keyword_extractor import extract_keywords
from app.services.web_agent.research_orchestrator import research_topics
from app.services.web_agent.topic_extraction import detect_topics

log = get_logger("hybrid_pipeline")


def _merge_topic_results(
    topic: str, web_result: ComponentTopicResult | None, kb_result: ComponentTopicResult | None
) -> ComponentTopicResult:
    """Combine a web-sourced and KB-sourced result for the same topic into one block."""
    web_result = web_result or ComponentTopicResult(topic=topic, keywords=[], extractive_summary=[], sources=[])
    kb_result = kb_result or ComponentTopicResult(topic=topic, keywords=[], extractive_summary=[], sources=[])

    merged_snippets = sorted(
        web_result.extractive_summary + kb_result.extractive_summary,
        key=lambda s: s.relevance_score,
        reverse=True,
    )
    merged_sources = kb_result.sources + web_result.sources  # KB first: "your own data" prioritized visually

    # Merge keywords by keyword text, keeping the higher score, then re-sort.
    kw_map: dict[str, float] = {}
    for kw in web_result.keywords + kb_result.keywords:
        kw_map[kw.keyword.lower()] = max(kw_map.get(kw.keyword.lower(), 0.0), kw.score)
    merged_keywords = [KeywordHit(keyword=k, score=v) for k, v in kw_map.items()]
    merged_keywords.sort(key=lambda k: k.score, reverse=True)

    return ComponentTopicResult(
        topic=topic,
        keywords=merged_keywords[: get_settings().keybert_top_n],
        extractive_summary=merged_snippets,
        sources=merged_sources,
    )


async def run_hybrid_research(
    query: str,
    include_web: bool = True,
    include_kb: bool = True,
    max_web_results: int | None = None,
) -> ResearchResponse:
    timings: dict[str, float] = {}
    warnings: list[str] = []

    t0 = time.perf_counter()
    topics = detect_topics(query)
    timings["topic_extraction_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    log.info(f"Query decomposed into {len(topics)} topics: {topics}")

    web_task = None
    kb_task = None

    t1 = time.perf_counter()

    if include_web:
        web_task = asyncio.create_task(research_topics(topics, max_results=max_web_results))
    else:
        warnings.append("Web research agent was disabled for this request.")

    if include_kb:
        if kb_document_count() == 0:
            warnings.append(
                "Knowledge base is empty — run the ingestion script "
                "(scripts/ingest_datasheets.py) to index datasheets."
            )
        # KB query is CPU-bound (embeddings) and fast; run in a thread so it
        # doesn't block the event loop while the web task awaits network IO.
        kb_task = asyncio.create_task(asyncio.to_thread(research_topics_in_kb, topics))
    else:
        warnings.append("Knowledge base lookup was disabled for this request.")

    web_results: list[ComponentTopicResult] = await web_task if web_task else []
    timings["web_research_ms"] = round((time.perf_counter() - t1) * 1000, 1)

    t2 = time.perf_counter()
    kb_results: list[ComponentTopicResult] = await kb_task if kb_task else []
    timings["kb_research_ms"] = round((time.perf_counter() - t2) * 1000, 1)

    # Index by topic for merging (both lists are in the same `topics` order,
    # but defend against length mismatches from partial failures anyway).
    web_by_topic = {r.topic: r for r in web_results}
    kb_by_topic = {r.topic: r for r in kb_results}

    t3 = time.perf_counter()
    merged_results = [
        _merge_topic_results(topic, web_by_topic.get(topic), kb_by_topic.get(topic)) for topic in topics
    ]
    timings["merge_ms"] = round((time.perf_counter() - t3) * 1000, 1)

    # Global keyword summary: extracted directly from the raw query so it
    # reflects the user's actual ask, independent of how research went.
    global_kw = extract_keywords(query)
    global_keywords = [KeywordHit(keyword=k.keyword, score=k.score) for k in global_kw]

    # Deduplicate sources across topics for the flat `all_sources` list.
    seen_ids = set()
    all_sources: list[ResearchSource] = []
    for topic_result in merged_results:
        for src in topic_result.sources:
            if src.id not in seen_ids:
                seen_ids.add(src.id)
                all_sources.append(src)

    timings["total_ms"] = round(sum(v for k, v in timings.items() if k != "total_ms"), 1)

    return ResearchResponse(
        query=query,
        detected_topics=topics,
        global_keywords=global_keywords,
        results_by_topic=merged_results,
        all_sources=all_sources,
        web_agent_used=include_web,
        kb_used=include_kb,
        timing_ms=timings,
        warnings=warnings,
    )
