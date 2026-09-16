"""
Orchestrates the full ingestion pipeline for one paper: download PDF,
extract text, chunk, embed, store in ChromaDB. A small JSON cache marker
per paper means re-ingesting the same paper is a fast no-op instead of
re-downloading and re-embedding everything.
"""
import json
import logging
from pathlib import Path

from app.core.config import settings
from app.schemas.ingest import IngestStatus
from app.schemas.paper import Paper
from ingestion.chunker import chunk_text
from ingestion.pdf_downloader import PdfDownloadError, download_pdf
from ingestion.text_extractor import PdfExtractionError, ScannedPdfError, extract_text
from ingestion.vector_store import upsert_chunks

logger = logging.getLogger(__name__)


def make_paper_id(paper: Paper) -> str:
    """A stable, filesystem-safe unique ID for a paper, e.g. 'arxiv_1706.03762'."""
    safe_external_id = paper.external_id.replace("/", "_")
    return f"{paper.source.value}_{safe_external_id}"


def _cache_marker_path(paper_id: str) -> Path:
    return Path(settings.cache_dir) / "ingested" / f"{paper_id}.json"


def _pdf_path(paper_id: str) -> Path:
    return Path(settings.papers_dir) / f"{paper_id}.pdf"


def _read_cache_marker(paper_id: str) -> dict | None:
    marker = _cache_marker_path(paper_id)
    if not marker.exists():
        return None
    try:
        return json.loads(marker.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Corrupt cache marker for %s, ignoring", paper_id)
        return None


def _write_cache_marker(paper_id: str, data: dict) -> None:
    marker = _cache_marker_path(paper_id)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(data), encoding="utf-8")


def _paper_metadata_path(paper_id: str) -> Path:
    return Path(settings.cache_dir) / "paper_metadata" / f"{paper_id}.json"


def save_paper_metadata(paper_id: str, paper: Paper) -> None:
    """
    Persists full paper metadata (authors, DOI, year, etc.) keyed by
    paper_id, independent of ingestion success/failure. Phase 3's citation
    generator reads this back, so a summary can be requested with just a
    paper_id rather than resending the whole paper object every time.
    """
    path = _paper_metadata_path(paper_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(paper.model_dump_json(), encoding="utf-8")


def load_paper_metadata(paper_id: str) -> Paper | None:
    path = _paper_metadata_path(paper_id)
    if not path.exists():
        return None
    try:
        return Paper.model_validate_json(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, ValueError):
        logger.warning("Corrupt paper metadata for %s, ignoring", paper_id)
        return None

async def ingest_paper(paper: Paper, force: bool = False) -> dict:
    """
    Runs the full pipeline for one paper. Returns a dict matching
    IngestResponse's fields (kept as a dict here so this stays independent
    of the API layer). Never raises - every failure mode is caught and
    returned as a status the caller can act on or display.
    """
    paper_id = make_paper_id(paper)
    save_paper_metadata(paper_id, paper)

    if not force:
        cached = _read_cache_marker(paper_id)
        if cached is not None:
            logger.info("Paper %s already ingested, skipping (use force=True to redo)", paper_id)
            return {
                "paper_id": paper_id,
                "status": IngestStatus.ALREADY_CACHED,
                "chunk_count": cached.get("chunk_count", 0),
                "page_count": cached.get("page_count"),
                "message": "Already ingested; pass force=true to re-process.",
            }

    if not paper.pdf_url:
        logger.info("No PDF URL available for paper_id=%s", paper_id)
        return {
            "paper_id": paper_id,
            "status": IngestStatus.NO_PDF_AVAILABLE,
            "chunk_count": 0,
            "message": "This source did not provide a PDF link for this paper.",
        }

    pdf_path = _pdf_path(paper_id)
    try:
        await download_pdf(paper.pdf_url, pdf_path)
    except PdfDownloadError as exc:
        return {
            "paper_id": paper_id,
            "status": IngestStatus.DOWNLOAD_FAILED,
            "chunk_count": 0,
            "message": str(exc),
        }

    try:
        extracted = extract_text(pdf_path)
    except ScannedPdfError as exc:
        return {
            "paper_id": paper_id,
            "status": IngestStatus.SCANNED_PDF,
            "chunk_count": 0,
            "message": str(exc),
        }
    except PdfExtractionError as exc:
        return {
            "paper_id": paper_id,
            "status": IngestStatus.EXTRACTION_FAILED,
            "chunk_count": 0,
            "message": str(exc),
        }

    chunks = chunk_text(extracted.full_text)
    chunk_count = upsert_chunks(paper_id=paper_id, title=paper.title, chunks=chunks)

    result = {
        "paper_id": paper_id,
        "status": IngestStatus.SUCCESS,
        "chunk_count": chunk_count,
        "page_count": extracted.page_count,
        "message": None,
    }
    _write_cache_marker(paper_id, {"chunk_count": chunk_count, "page_count": extracted.page_count})
    return result