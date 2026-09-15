"""
Wraps a local sentence-transformers embedding model. Loaded lazily and
cached as a module-level singleton so the ~80MB model is only loaded once
per process, not once per request.
"""
import logging

from sentence_transformers import SentenceTransformer

from app.core.config import settings

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        logger.info("Loading embedding model %s (first call only)...", settings.embedding_model)
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    vectors = model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return vectors.tolist()