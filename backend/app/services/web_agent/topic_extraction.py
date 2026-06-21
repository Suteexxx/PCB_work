"""
Topic / component extraction for electronics design prompts.

A real design prompt ("ultra low noise current source using a Howland /
Libbrecht-Hall topology, zero-drift opamps, precision resistors, LDOs...")
bundles many distinct research topics into one sentence. Asking the search
agent to research the whole sentence at once produces shallow, blended
results. Instead we:

  1. Detect known electronics component/topology phrases via a curated
     gazetteer (regex/alias-based, fast, no model needed).
  2. Fall back to KeyBERT noun-phrase extraction for anything not in the
     gazetteer, so unfamiliar component names still get picked up.
  3. Always keep the *original full query* as one of the topics too, so a
     holistic "system-level" search still happens alongside per-component ones.

This keeps everything deterministic and explainable -- important for an
engineering tool where the user needs to trust *why* a result showed up.
"""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("topic_extraction")

# --------------------------------------------------------------------------- #
# Curated electronics gazetteer.
# Maps a canonical topic name -> regex alternatives that should trigger it.
# Extend this list freely as you encounter new domains (op-amps, filters,
# PSU topologies, sensor types, etc.) -- it's the cheapest way to improve
# extraction quality without touching any code logic.
# --------------------------------------------------------------------------- #
COMPONENT_GAZETTEER: dict[str, list[str]] = {
    "Howland / Libbrecht-Hall current source": [
        r"libbrecht[\s-]?hall",
        r"howland current (pump|source)",
        r"improved howland",
    ],
    "Zero-drift / chopper op-amp": [
        r"zero[\s-]?drift op[\s-]?amp",
        r"chopper[\s-]?stabilized op[\s-]?amp",
        r"chopper[\s-]?stabilized amplifier",
        r"auto[\s-]?zero op[\s-]?amp",
    ],
    "Ultra-precision resistor": [
        r"ultra[\s-]?precision resistor",
        r"precision resistor",
        r"low (?:tcr|drift) resistor",
        r"bulk metal foil resistor",
    ],
    "Low-dropout regulator (LDO)": [
        r"\bldos?\b",
        r"low[\s-]?dropout regulator",
        r"linear voltage regulator",
    ],
    "Voltage reference": [
        r"voltage reference",
        r"\bbandgap\b",
        r"buried zener reference",
    ],
    "Current source / current sink design": [
        r"current source",
        r"current sink",
        r"current pump",
        r"constant current circuit",
    ],
    "Negative voltage generation / charge pump": [
        r"negative voltage generat",
        r"charge pump",
        r"inverting regulator",
        r"split rail (?:supply|power)",
        r"dual[\s-]?polarity",
        r"\bpolarit(?:y|ies)\b",
        r"bipolar (?:rail|supply)",
    ],
    "Current noise / 1/f noise analysis": [
        r"current noise",
        r"noise density",
        r"1/f noise",
        r"flicker noise",
        r"output noise estimat",
    ],
    "Potentiometer-based current/voltage adjustment": [
        r"potentiometer",
        r"trim(?:ming)? resistor",
        r"digital potentiometer",
    ],
    "Single supply / single rail power design": [
        r"single (?:dc )?supply",
        r"single rail",
        r"single dc input",
        r"split supply from single",
    ],
    "PCB layout for low noise analog circuits": [
        r"low noise pcb layout",
        r"analog layout guideline",
        r"ground plane (?:design|layout)",
        r"guard ring",
    ],
}

_COMPILED_GAZETTEER = {
    topic: [re.compile(pat, re.IGNORECASE) for pat in patterns]
    for topic, patterns in COMPONENT_GAZETTEER.items()
}


def extract_known_topics(query: str) -> list[str]:
    """Return canonical topic names whose gazetteer patterns match the query."""
    hits = []
    for topic, patterns in _COMPILED_GAZETTEER.items():
        if any(p.search(query) for p in patterns):
            hits.append(topic)
    return hits


def extract_keyphrase_topics(query: str, exclude: list[str] | None = None, top_n: int = 6) -> list[str]:
    """
    KeyBERT-based fallback: pull candidate noun-phrase keywords from the raw
    query so components NOT in the gazetteer still get researched.
    Lazily imports KeyBERT to keep module import time fast when unused.
    """
    from app.services.web_agent.keyword_extractor import extract_keywords  # local import, avoids cycle

    settings = get_settings()
    kw_hits = extract_keywords(query, top_n=top_n or settings.keybert_top_n)
    exclude_lower = {e.lower() for e in (exclude or [])}

    topics = []
    for kw in kw_hits:
        phrase = kw.keyword.strip()
        if len(phrase) < 4:
            continue
        if any(phrase.lower() in ex.lower() or ex.lower() in phrase.lower() for ex in exclude_lower):
            continue
        topics.append(phrase)
    return topics


def detect_topics(query: str, max_topics: int = 8) -> list[str]:
    """
    Main entrypoint: returns an ordered, deduplicated list of research topics
    derived from a free-form design query.

    Order: gazetteer matches first (high confidence, human-readable labels),
    then keyphrase fallbacks to fill remaining slots, capped at max_topics.
    """
    known = extract_known_topics(query)
    log.info(f"Gazetteer matched {len(known)} known topics: {known}")

    remaining_slots = max(max_topics - len(known), 0)
    keyphrases = []
    if remaining_slots > 0:
        keyphrases = extract_keyphrase_topics(query, exclude=known, top_n=remaining_slots + 2)

    combined = known + keyphrases
    # Dedup while preserving order
    seen = set()
    deduped = []
    for t in combined:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(t)

    return deduped[:max_topics] if deduped else [query]
