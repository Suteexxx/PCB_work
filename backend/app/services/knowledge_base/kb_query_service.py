"""
Knowledge base query service.

Wraps vector_store.query_kb() and reshapes raw Chroma output into the same
ComponentTopicResult / CitedSnippet / ResearchSource shapes the web agent
produces, so the API layer can merge both sources transparently.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import CitedSnippet, ComponentTopicResult, KeywordHit, ResearchSource, SourceType
from app.services.knowledge_base.vector_store import query_kb
from app.services.web_agent.keyword_extractor import extract_keywords
from app.utils.url_utils import make_id

log = get_logger("kb_query_service")


def research_topic_in_kb(topic: str, top_k: int | None = None) -> ComponentTopicResult:
    """Semantic search the local datasheet KB for a given topic/component."""
    settings = get_settings()
    top_k = top_k or settings.kb_top_k

    raw = query_kb(topic, top_k=top_k)

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    if not documents:
        return ComponentTopicResult(topic=topic, keywords=[], extractive_summary=[], sources=[])

    sources: dict[str, ResearchSource] = {}
    snippets: list[CitedSnippet] = []
    combined_text_parts = []

    for doc_text, meta, distance in zip(documents, metadatas, distances):
        file_name = meta.get("file_name", "unknown.pdf")
        source_id = make_id("kb", file_name)

        # Chroma cosine "distance" -> similarity (0..1, higher = better)
        similarity = max(0.0, 1.0 - float(distance))

        if source_id not in sources:
            sources[source_id] = ResearchSource(
                id=source_id,
                title=meta.get("title", file_name),
                source_type=SourceType.KNOWLEDGE_BASE,
                url=None,
                file_name=file_name,
                domain=None,
                fetched_at=None,
                snippet_count=0,
            )

        snippets.append(CitedSnippet(text=doc_text[:500], relevance_score=round(similarity, 4), source_id=source_id))
        sources[source_id].snippet_count += 1
        combined_text_parts.append(doc_text)

    snippets.sort(key=lambda s: s.relevance_score, reverse=True)

    combined_text = " ".join(combined_text_parts)[:6000]
    kw_hits = extract_keywords(combined_text, top_n=settings.keybert_top_n)
    keywords = [KeywordHit(keyword=k.keyword, score=k.score) for k in kw_hits]

    return ComponentTopicResult(
        topic=topic,
        keywords=keywords,
        extractive_summary=snippets,
        sources=list(sources.values()),
    )


def research_topics_in_kb(topics: list[str], top_k: int | None = None) -> list[ComponentTopicResult]:
    return [research_topic_in_kb(t, top_k=top_k) for t in topics]
