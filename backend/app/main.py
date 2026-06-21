"""
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
(from the backend/ directory, with the virtualenv activated)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import knowledge_base, research
from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"{settings.app_name} starting up...")
    # Pre-warm the embedding model so the first real request isn't slow.
    from app.core.embeddings import get_embedding_model

    try:
        get_embedding_model()
        log.info("Embedding model pre-warmed.")
    except Exception as e:
        log.warning(
            f"Embedding model could not be pre-warmed at startup ({e}). "
            "It will be lazily loaded on first request instead."
        )
    log.info("Startup complete.")
    yield
    log.info(f"{settings.app_name} shutting down.")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Hybrid research backend for PCB/circuit design automation. "
        "Combines a local ChromaDB datasheet knowledge base with a free, "
        "local web research agent (DuckDuckGo search + scraping + "
        "embedding-based extractive summarization) to gather component "
        "and topology information for a given design prompt."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router, prefix=settings.api_v1_prefix)
app.include_router(knowledge_base.router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["root"])
async def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
        "api_prefix": settings.api_v1_prefix,
    }
