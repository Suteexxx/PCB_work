"""
ChromaDB-backed vector store for the local datasheet knowledge base.

Datasheets are chunked (utils.text_processing.chunk_by_words), embedded
with the SAME embedding model used by the web agent, and stored in a
persistent Chroma collection on disk (backend/data/chroma_kb). This lets
the hybrid pipeline run semantic search over your own PDFs alongside live
web results.
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings
from app.core.embeddings import embed_texts
from app.core.logging import get_logger

log = get_logger("vector_store")

_client: chromadb.ClientAPI | None = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        settings = get_settings()
        settings.chroma_kb_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(settings.chroma_kb_dir),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_kb_collection():
    settings = get_settings()
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=settings.kb_collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    chunk_ids: list[str],
    chunk_texts: list[str],
    metadatas: list[dict],
) -> None:
    """Embed and upsert chunks into the KB collection."""
    if not chunk_texts:
        return
    collection = get_kb_collection()
    vectors = embed_texts(chunk_texts)
    collection.upsert(
        ids=chunk_ids,
        embeddings=vectors.tolist(),
        documents=chunk_texts,
        metadatas=metadatas,
    )
    log.info(f"Upserted {len(chunk_texts)} chunks into KB collection")


def query_kb(query_text: str, top_k: int | None = None) -> dict:
    """Semantic search over the KB. Returns raw Chroma query result dict."""
    settings = get_settings()
    top_k = top_k or settings.kb_top_k
    collection = get_kb_collection()

    count = collection.count()
    if count == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    query_vec = embed_texts([query_text])[0].tolist()
    return collection.query(
        query_embeddings=[query_vec],
        n_results=min(top_k, count),
    )


def kb_document_count() -> int:
    try:
        return get_kb_collection().count()
    except Exception:
        return 0


def reset_kb() -> None:
    """Delete and recreate the KB collection (used by re-ingestion scripts)."""
    settings = get_settings()
    client = get_chroma_client()
    try:
        client.delete_collection(settings.kb_collection_name)
    except Exception:
        pass
    get_kb_collection()
    log.info("KB collection reset")
