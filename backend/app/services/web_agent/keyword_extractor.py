"""
Keyword extraction using KeyBERT (built on the same SentenceTransformer
embedding model used everywhere else, so it shares the singleton -- no
extra model load cost).

This is the "marks the keywords" part of the pipeline: given a chunk of
scraped or query text, surface the phrases that best represent it.
"""

from __future__ import annotations

from dataclasses import dataclass

from keybert import KeyBERT

from app.core.config import get_settings
from app.core.embeddings import get_embedding_model
from app.core.logging import get_logger

log = get_logger("keyword_extractor")

_kw_model: KeyBERT | None = None


@dataclass
class KeywordResult:
    keyword: str
    score: float


def _get_keybert() -> KeyBERT:
    global _kw_model
    if _kw_model is None:
        log.info("Initializing KeyBERT on shared embedding model...")
        _kw_model = KeyBERT(model=get_embedding_model())
    return _kw_model


# Generic stopword-ish filler terms common in scraped marketing/footer text
# that KeyBERT sometimes surfaces and that add no engineering value.
_JUNK_TERMS = {
    "click here", "read more", "learn more", "privacy policy", "cookie",
    "all rights reserved", "sign up", "subscribe", "terms of use",
}


def extract_keywords(
    text: str,
    top_n: int | None = None,
    ngram_range: tuple[int, int] | None = None,
) -> list[KeywordResult]:
    """Extract top-N keyphrases from text via KeyBERT's MMR-diversified search."""
    settings = get_settings()
    top_n = top_n or settings.keybert_top_n
    ngram_range = ngram_range or settings.keyword_ngram_range

    text = (text or "").strip()
    if len(text) < 15:
        return []

    model = _get_keybert()
    try:
        raw_hits = model.extract_keywords(
            text,
            keyphrase_ngram_range=ngram_range,
            stop_words="english",
            use_mmr=True,
            diversity=0.55,
            top_n=top_n,
        )
    except Exception as e:
        log.warning(f"KeyBERT extraction failed, returning empty: {e}")
        return []

    results = []
    for phrase, score in raw_hits:
        if phrase.lower() in _JUNK_TERMS:
            continue
        results.append(KeywordResult(keyword=phrase, score=round(float(score), 4)))
    return results
