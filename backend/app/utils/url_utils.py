"""URL helpers: domain extraction, dedup keys, ID generation."""

from __future__ import annotations

import hashlib
from urllib.parse import urlparse


def get_domain(url: str) -> str:
    """Extract a clean domain (no www., no scheme) from a URL."""
    try:
        netloc = urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return "unknown"


def make_id(*parts: str) -> str:
    """Deterministic short ID from arbitrary string parts (used for source IDs)."""
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
