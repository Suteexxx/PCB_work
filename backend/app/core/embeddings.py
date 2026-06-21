"""
Shared SentenceTransformer embedding model.

Both the knowledge base (datasheet) pipeline and the live web research
pipeline must embed text into the SAME vector space so that scores are
comparable when results are merged. This module loads the model exactly
once (process-wide singleton) and exposes thin helper functions.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger("embeddings")

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the SentenceTransformer model."""
    global _model
    if _model is None:
        settings = get_settings()
        log.info(f"Loading embedding model '{settings.embedding_model_name}'...")
        _model = SentenceTransformer(
            settings.embedding_model_name, device=settings.embedding_device
        )
        log.info("Embedding model loaded.")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts -> (n, dim) float32 normalized array."""
    if not texts:
        return np.zeros((0, get_embedding_model().get_sentence_embedding_dimension()))
    model = get_embedding_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,  # so dot product == cosine similarity
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors


def cosine_sim_matrix(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    """Cosine similarity between a single query vector and many doc vectors.

    Assumes inputs are already L2-normalized (embed_texts does this).
    """
    if doc_vecs.shape[0] == 0:
        return np.zeros((0,))
    return doc_vecs @ query_vec
