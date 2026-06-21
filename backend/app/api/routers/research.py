"""
Research API router.

Exposes the hybrid pipeline (KB + web research agent) as a REST endpoint
the Streamlit frontend (or anything else) can call.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.models.schemas import ResearchRequest, ResearchResponse
from app.services.hybrid_pipeline import run_hybrid_research

log = get_logger("research_router")

router = APIRouter(prefix="/research", tags=["research"])


@router.post("", response_model=ResearchResponse, summary="Run hybrid component/topic research on a design prompt")
async def research(request: ResearchRequest) -> ResearchResponse:
    """
    Main entrypoint: takes a free-form PCB/circuit design prompt, decomposes
    it into component/topology topics, and researches each topic against
    the local datasheet knowledge base and/or the live web.
    """
    if not request.include_web and not request.include_kb:
        raise HTTPException(status_code=400, detail="At least one of include_web or include_kb must be true.")

    try:
        return await run_hybrid_research(
            query=request.query,
            include_web=request.include_web,
            include_kb=request.include_kb,
            max_web_results=request.max_web_results,
        )
    except Exception as e:
        log.exception("Hybrid research pipeline failed")
        raise HTTPException(status_code=500, detail=f"Research pipeline error: {e}") from e
