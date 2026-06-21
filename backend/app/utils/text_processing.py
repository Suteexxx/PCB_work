"""
Text processing utilities shared across the web agent and the knowledge base:
sentence splitting, word-chunking for long documents, and basic cleanup.

Uses NLTK's punkt tokenizer for sentence splitting (downloaded on first run
via scripts/setup_nltk.py or lazily here as a fallback).
"""

from __future__ import annotations

import re

import nltk

_PUNKT_READY = False


def _ensure_punkt() -> None:
    global _PUNKT_READY
    if _PUNKT_READY:
        return
    for resource in ("punkt", "punkt_tab"):
        try:
            nltk.data.find(f"tokenizers/{resource}")
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                pass  # offline fallback handled by split_sentences()
    _PUNKT_READY = True


_WHITESPACE_RE = re.compile(r"\s+")
_FALLBACK_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def clean_text(text: str) -> str:
    """Collapse whitespace, strip control characters."""
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("\u200b", " ")
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Falls back to regex if NLTK data is unavailable."""
    text = clean_text(text)
    if not text:
        return []

    _ensure_punkt()
    try:
        sentences = nltk.sent_tokenize(text)
    except Exception:
        sentences = _FALLBACK_SENTENCE_SPLIT_RE.split(text)

    return [s.strip() for s in sentences if s.strip()]


def chunk_by_words(text: str, chunk_size: int = 180, overlap: int = 30) -> list[str]:
    """Split long text into overlapping word-windows for embedding/indexing.

    Overlap preserves context across chunk boundaries so a fact split across
    two chunks is still retrievable.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    words = cleaned.split(" ")
    if len(words) <= chunk_size:
        return [" ".join(words)] if words else []

    chunks = []
    step = max(chunk_size - overlap, 1)
    for start in range(0, len(words), step):
        chunk_words = words[start : start + chunk_size]
        if not chunk_words:
            continue
        chunks.append(" ".join(chunk_words))
        if start + chunk_size >= len(words):
            break
    return chunks


def is_meaningful_sentence(sentence: str, min_words: int = 6) -> bool:
    """Filter out nav-bar junk, cookie banners, single-word fragments, etc."""
    words = sentence.split()
    if len(words) < min_words:
        return False
    # reject sentences that are mostly punctuation/symbols
    alpha_chars = sum(c.isalpha() for c in sentence)
    if alpha_chars < max(10, len(sentence) * 0.4):
        return False
    return True
