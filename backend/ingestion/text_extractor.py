"""
Extracts full text from a downloaded PDF using PyMuPDF (fitz).
Detects the "scanned PDF with no real text layer" edge case, since that
needs OCR (out of scope for now) rather than silently returning junk.
"""
import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# If the average extracted text per page is below this, we treat the PDF
# as scanned/image-only rather than trusting the (near-empty) text.
MIN_CHARS_PER_PAGE_THRESHOLD = 50


class PdfExtractionError(Exception):
    """Raised when a PDF is corrupt/unreadable."""


class ScannedPdfError(Exception):
    """Raised when a PDF has no meaningful extractable text layer (likely scanned)."""


@dataclass
class ExtractedDocument:
    full_text: str
    page_count: int
    pages: list[str]  # text per page, in order


def extract_text(pdf_path: Path) -> ExtractedDocument:
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.warning("Failed to open PDF %s: %s", pdf_path, exc)
        raise PdfExtractionError(f"Could not open PDF: {pdf_path}") from exc

    try:
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text().strip())
    finally:
        doc.close()

    full_text = "\n\n".join(pages)
    page_count = len(pages)

    if page_count == 0 or (len(full_text) / max(page_count, 1)) < MIN_CHARS_PER_PAGE_THRESHOLD:
        logger.info(
            "PDF %s looks scanned/image-only (%d pages, %d chars total)",
            pdf_path,
            page_count,
            len(full_text),
        )
        raise ScannedPdfError(
            f"PDF appears to have no extractable text layer (likely scanned): {pdf_path}"
        )

    return ExtractedDocument(full_text=full_text, page_count=page_count, pages=pages)