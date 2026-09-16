"""
Thin wrapper around a persistent ChromaDB collection. Each chunk is
stored with its embedding plus metadata (paper_id, chunk_index, title) so
later phases (summary generation, comparison) can filter/retrieve by
paper without re-embedding anything.
"""
import logging

import chromadb

from app.core.config import settings
from ingestion.embeddings import embed_texts

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_COLLECTION_NAME = "paper_chunks"


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(_COLLECTION_NAME)


def upsert_chunks(paper_id: str, title: str, chunks: list[str]) -> int:
    """
    Embeds and stores chunks for a paper. Existing chunks for this
    paper_id are deleted first, so re-ingesting a paper never duplicates
    entries. Returns the number of chunks stored.
    """
    if not chunks:
        return 0

    collection = _get_collection()

    # Clear any previous chunks for this paper (safe no-op if none exist).
    collection.delete(where={"paper_id": paper_id})

    embeddings = embed_texts(chunks)
    ids = [f"{paper_id}::chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"paper_id": paper_id, "title": title, "chunk_index": i} for i in range(len(chunks))
    ]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    logger.info("Stored %d chunks for paper_id=%s in ChromaDB", len(chunks), paper_id)
    return len(chunks)


def get_chunk_count(paper_id: str) -> int:
    collection = _get_collection()
    result = collection.get(where={"paper_id": paper_id})
    return len(result["ids"])


def get_chunks_for_paper(paper_id: str, limit: int | None = None) -> list[str]:
    """
    Returns a paper's stored chunks, ordered by their original position in
    the document (chunk_index), so the LLM sees the paper roughly in the
    order it was written rather than in random storage order. If `limit`
    is given, returns the first N chunks - early chunks (abstract, intro)
    are usually the most information-dense for a summary, so a simple
    "take the first N" is a reasonable default over a fancier relevance
    search for this phase.
    """
    collection = _get_collection()
    result = collection.get(where={"paper_id": paper_id}, include=["documents", "metadatas"])

    if not result["ids"]:
        return []

    paired = list(zip(result["metadatas"], result["documents"]))
    paired.sort(key=lambda pair: pair[0]["chunk_index"])
    ordered_chunks = [doc for _, doc in paired]

    if limit is not None:
        return ordered_chunks[:limit]
    return ordered_chunks