"""
Pydantic schemas defining the research API contract.

These are the shapes the frontend (Streamlit) and backend (FastAPI) agree
on. Keeping them in one place means both layers stay in sync and the
OpenAPI docs (/docs) are auto-generated and accurate.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


# --------------------------------------------------------------------------- #
# Request
# --------------------------------------------------------------------------- #

class ResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=8,
        description="Free-form design prompt, e.g. 'design an ultra low noise "
        "current source for 100mA using Howland current pump...'",
    )
    max_web_results: int | None = Field(
        default=None, ge=1, le=20, description="Override default web result count"
    )
    include_web: bool = Field(default=True, description="Run the live web research agent")
    include_kb: bool = Field(default=True, description="Query the local datasheet knowledge base")


# --------------------------------------------------------------------------- #
# Shared sub-objects
# --------------------------------------------------------------------------- #

class SourceType(str, Enum):
    WEB = "web"
    KNOWLEDGE_BASE = "knowledge_base"


class CitedSnippet(BaseModel):
    """One extractive sentence/claim tied back to its originating source."""

    text: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    source_id: str  # links back to a ResearchSource.id


class ResearchSource(BaseModel):
    """A single document the agent pulled information from."""

    id: str
    title: str
    source_type: SourceType
    url: HttpUrl | None = None  # None for KB / local PDF sources
    file_name: str | None = None  # set for KB sources
    domain: str | None = None
    fetched_at: str | None = None
    snippet_count: int = 0


class KeywordHit(BaseModel):
    keyword: str
    score: float = Field(..., ge=0.0, le=1.0)


class ComponentTopicResult(BaseModel):
    """Research results scoped to one identified component/topic in the query.

    For a query mentioning "zero drift opamp" and "ultra precision resistor"
    and "LDO", we split research per component so the output is organized
    the way a real engineer would want to read it (not one giant blob).
    """

    topic: str
    keywords: list[KeywordHit]
    extractive_summary: list[CitedSnippet]
    sources: list[ResearchSource]


# --------------------------------------------------------------------------- #
# Response
# --------------------------------------------------------------------------- #

class ResearchResponse(BaseModel):
    query: str
    detected_topics: list[str]
    global_keywords: list[KeywordHit]
    results_by_topic: list[ComponentTopicResult]
    all_sources: list[ResearchSource]
    web_agent_used: bool
    kb_used: bool
    timing_ms: dict[str, float]
    warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Health / misc
# --------------------------------------------------------------------------- #

class HealthResponse(BaseModel):
    status: str
    embedding_model: str
    kb_documents_indexed: int


class KBIngestResponse(BaseModel):
    files_ingested: int
    chunks_indexed: int
    skipped: list[str] = Field(default_factory=list)
