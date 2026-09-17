"""
Provides the embedding function used by ChromaDB. Uses ChromaDB's
built-in ONNX-based embedding function instead of sentence-transformers
(PyTorch) - same underlying model family and embedding quality for our
use case, but without pulling in PyTorch's much heavier memory footprint.
This matters specifically for fitting comfortably within free-tier
hosting memory limits (e.g. Render's 512MB free tier).
"""
import logging

from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

_embedding_function = None


def get_embedding_function():
    """
    Returns a lazily-created, cached ChromaDB embedding function backed by
    ONNX Runtime. Passed directly to a ChromaDB collection so ChromaDB
    handles embedding internally - we no longer call an embed step
    ourselves before storing chunks.
    """
    global _embedding_function
    if _embedding_function is None:
        logger.info("Loading ONNX embedding function (first call only)...")
        _embedding_function = embedding_functions.ONNXMiniLM_L6_V2()
    return _embedding_function