from enum import Enum

from pydantic import BaseModel

from app.schemas.paper import Paper


class IngestStatus(str, Enum):
    SUCCESS = "success"
    ALREADY_CACHED = "already_cached"
    NO_PDF_AVAILABLE = "no_pdf_available"
    DOWNLOAD_FAILED = "download_failed"
    EXTRACTION_FAILED = "extraction_failed"
    SCANNED_PDF = "scanned_pdf"


class IngestRequest(BaseModel):
    paper: Paper
    force: bool = False  # bypass cache and re-ingest even if already processed


class IngestResponse(BaseModel):
    paper_id: str
    status: IngestStatus
    chunk_count: int = 0
    page_count: int | None = None
    message: str | None = None