"""Embedding service using fastembed with intfloat/multilingual-e5-large.

The model is cached as a module-level singleton via lru_cache so the
first call downloads and loads it, and subsequent calls reuse the same
instance within a process.

Reference: Wang et al. (2024). "Multilingual E5 Text Embeddings:
A Technical Report". arXiv:2402.05672.

Note: the original plan specified BAAI/bge-m3 but fastembed 0.8.0
does not include that model. intfloat/multilingual-e5-large is the
closest alternative: multilingual, 1024-dim, ONNX-based, and
available in fastembed out of the box.
"""
from __future__ import annotations

import logging
from functools import lru_cache

from django.conf import settings

from .versions import EMBEDDING_DIM, EMBEDDING_MODEL

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model():
    """Return the singleton TextEmbedding instance."""
    from fastembed import TextEmbedding
    logger.info("Loading embedding model %s", EMBEDDING_MODEL)
    return TextEmbedding(model_name=EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts into 1024-dimensional vectors.

    Returns an empty list for empty input.
    """
    if not texts:
        return []

    model = get_embedding_model()
    batch_size = getattr(settings, "EPOCHA_KG_EMBEDDING_BATCH_SIZE", 10)

    vectors: list[list[float]] = []
    for vector in model.embed(texts, batch_size=batch_size):
        vectors.append([float(x) for x in vector])

    return vectors
