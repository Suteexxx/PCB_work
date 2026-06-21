"""
Extractive summarization via embedding-based sentence ranking.

For each scraped page: split into sentences -> embed all sentences ->
cosine-similarity each against the topic query embedding -> keep the
top-K most relevant, meaningful sentences as "cited snippets".

This is what gives the "Claude/ChatGPT-style" feel (a synthesized-looking
answer with inline-citable claims) without doing any text generation --
every sentence returned is verbatim from the source, so it's always
traceable and never hallucinated.
"""

from __future__ import annotations

import numpy as np

from app.core.config import get_settings
from app.core.embeddings import embed_texts, cosine_sim_matrix
from app.core.logging import get_logger
from app.utils.text_processing import split_sentences, is_meaningful_sentence

log = get_logger("sentence_ranker")


def rank_sentences_against_query(
    sentences: list[str], query_vec: np.ndarray, top_k: int, min_score: float
) -> list[tuple[str, float]]:
    """Return up to top_k (sentence, score) pairs above min_score, sorted desc."""
    if not sentences:
        return []

    sent_vecs = embed_texts(sentences)
    scores = cosine_sim_matrix(query_vec, sent_vecs)

    ranked_idx = np.argsort(-scores)
    out = []
    for idx in ranked_idx:
        score = float(scores[idx])
        if score < min_score:
            break
        out.append((sentences[idx], round(score, 4)))
        if len(out) >= top_k:
            break
    return out


def build_extractive_snippets_for_page(
    page_text: str, topic_query: str
) -> list[tuple[str, float]]:
    """
    Full per-page pipeline: clean -> split sentences -> filter junk -> rank.
    Returns list of (sentence_text, relevance_score).
    """
    settings = get_settings()

    raw_sentences = split_sentences(page_text)
    meaningful = [
        s for s in raw_sentences if is_meaningful_sentence(s, settings.sentence_min_words)
    ]
    if not meaningful:
        return []

    query_vec = embed_texts([topic_query])[0]
    return rank_sentences_against_query(
        meaningful,
        query_vec,
        top_k=settings.top_sentences_per_source,
        min_score=settings.similarity_threshold,
    )
