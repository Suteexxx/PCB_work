"""
Lightweight disk-based TTL cache for web research results, keyed by
normalized query text. Avoids hammering DuckDuckGo / re-scraping the same
pages on repeated/iterative design queries during development.

Deliberately simple (JSON files on disk) -- no Redis dependency needed
for a single-process research tool.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("cache")


def _cache_key(topic: str) -> str:
    return hashlib.sha256(topic.strip().lower().encode("utf-8")).hexdigest()[:24]


def _cache_path(topic: str) -> Path:
    settings = get_settings()
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings.cache_dir / f"{_cache_key(topic)}.json"


def get_cached(topic: str) -> dict | None:
    settings = get_settings()
    path = _cache_path(topic)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if time.time() - payload.get("_cached_at", 0) > settings.cache_ttl_seconds:
        return None  # expired

    return payload.get("data")


def set_cached(topic: str, data: dict) -> None:
    path = _cache_path(topic)
    payload = {"_cached_at": time.time(), "topic": topic, "data": data}
    try:
        path.write_text(json.dumps(payload), encoding="utf-8")
    except Exception as e:
        log.warning(f"Failed to write cache for '{topic}': {e}")
