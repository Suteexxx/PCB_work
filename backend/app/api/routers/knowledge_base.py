"""
Knowledge base management router: health check + manual re-ingestion trigger.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import HealthResponse, KBIngestResponse
from app.services.knowledge_base.ingestion import ingest_directory
from app.services.knowledge_base.vector_store import kb_document_count, reset_kb

log = get_logger("kb_router")

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        embedding_model=settings.embedding_model_name,
        kb_documents_indexed=kb_document_count(),
    )


@router.post("/ingest", response_model=KBIngestResponse, summary="Re-ingest PDFs from the sample_datasheets directory")
async def ingest(reset: bool = False) -> KBIngestResponse:
    """
    Trigger (re-)ingestion of all PDFs in backend/data/sample_datasheets
    into the vector store. Pass ?reset=true to wipe the collection first
    (useful after changing chunking parameters).
    """
    try:
        if reset:
            reset_kb()
        result = ingest_directory()
        return KBIngestResponse(**result)
    except Exception as e:
        log.exception("KB ingestion failed")
        raise HTTPException(status_code=500, detail=f"Ingestion error: {e}") from e
