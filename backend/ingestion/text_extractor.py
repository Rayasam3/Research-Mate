"""
Reads a downloaded PDF and returns clean text, tables and figure captions.

How it works (simple version):
  1. PyMuPDF reads every page as "blocks" of text. Two-column papers are
     put back in the right reading order (left column, then right column).
  2. Tables are found with PyMuPDF's table finder and written as plain
     rows ("a | b | c") so numbers in results tables are not lost.
  3. Figure captions ("Fig. 3: ...") are collected, because the diagram
     itself cannot be read but its caption says what it shows.
  4. If PyMuPDF gets almost no text, we try pdfplumber, then pypdf.
  5. Page headers/footers that repeat on many pages are removed and
     words broken by a line-end hyphen ("auto-\\ncoders") are joined.

A PDF with no text layer at all (a scan) raises ScannedPdfError.
"""
import logging
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

# Average characters per page below this = scanned / image-only PDF.
MIN_CHARS_PER_PAGE_THRESHOLD = 50

# A block wider than this share of the page is a full-width block (title, abstract box).
FULL_WIDTH_RATIO = 0.6

_CAPTION_RE = re.compile(r"^\s*(fig\.?|figure|table)\s*\d+[.:)\s]", re.IGNORECASE)


class PdfExtractionError(Exception):
    """Raised when a PDF is corrupt/unreadable."""


class ScannedPdfError(Exception):
    """Raised when a PDF has no meaningful extractable text layer (likely scanned)."""


@dataclass
class ExtractedDocument:
    full_text: str
    page_count: int
    pages: list[str]                                   # cleaned text per page, in order
    tables: list[str] = field(default_factory=list)    # each table as "row | row" text
    figure_captions: list[str] = field(default_factory=list)
    image_count: int = 0                               # pictures found (diagrams, photos)
    method: str = "pymupdf"                            # which reader produced the text


# --------------------------------------------------------------------------
# Step 1: PyMuPDF with column-aware reading order
# --------------------------------------------------------------------------

def order_blocks(blocks: list[tuple], page_width: float) -> list[tuple]:
    """
    Puts text blocks in human reading order.
    Each block is (x0, y0, x1, y1, text). Full-width blocks (title, abstract
    box) split the page into bands; inside a band the left column is read
    before the right column.
    """
    blocks = sorted(blocks, key=lambda b: (b[1], b[0]))
    middle = page_width / 2
    ordered: list[tuple] = []
    left: list[tuple] = []
    right: list[tuple] = []

    def flush() -> None:
        ordered.extend(sorted(left, key=lambda b: b[1]))
        ordered.extend(sorted(right, key=lambda b: b[1]))
        left.clear()
        right.clear()

    for block in blocks:
        width = block[2] - block[0]
        if width >= FULL_WIDTH_RATIO * page_width:
            flush()
            ordered.append(block)
        elif block[0] < middle - 5 and block[2] <= middle + 20:
            left.append(block)
        elif block[0] >= middle - 20:
            right.append(block)
        else:
            flush()                 # a block that crosses the middle: treat as full width
            ordered.append(block)
    flush()
    return ordered


def _rows_to_text(rows: list[list]) -> str:
    lines = []
    for row in rows:
        cells = [re.sub(r"\s+", " ", str(c or "")).strip() for c in row]
        if any(cells):
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _inside(block: tuple, box: tuple) -> bool:
    """True if the block's centre lies inside the box."""
    cx, cy = (block[0] + block[2]) / 2, (block[1] + block[3]) / 2
    return box[0] <= cx <= box[2] and box[1] <= cy <= box[3]


def _read_page_pymupdf(page) -> tuple[str, list[str], int]:
    """Returns (page text, tables on this page, number of images)."""
    tables: list[str] = []
    table_boxes: list[tuple] = []
    try:
        for table in page.find_tables().tables:
            text = _rows_to_text(table.extract())
            if text.count("\n") >= 1:               # at least 2 rows, else it is not a table
                tables.append(text)
                table_boxes.append(tuple(table.bbox))
    except Exception:
        logger.debug("Table finder failed on a page", exc_info=True)

    raw_blocks = [
        (b[0], b[1], b[2], b[3], b[4])
        for b in page.get_text("blocks")
        if b[6] == 0 and b[4].strip()               # type 0 = text
    ]
    # Text that is inside a table is already in the table text: skip it here.
    raw_blocks = [b for b in raw_blocks if not any(_inside(b, box) for box in table_boxes)]

    text_parts = [b[4].strip() for b in order_blocks(raw_blocks, page.rect.width)]
    for table_text in tables:
        text_parts.append("[TABLE]\n" + table_text + "\n[/TABLE]")

    try:
        images = len(page.get_images(full=True))
    except Exception:
        images = 0
    return "\n".join(text_parts), tables, images


# --------------------------------------------------------------------------
# Step 2: fallback readers (only used when PyMuPDF finds almost no text)
# --------------------------------------------------------------------------

def _read_with_pdfplumber(pdf_path: Path) -> list[str] | None:
    try:
        import pdfplumber
    except ImportError:
        return None
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            return [(page.extract_text() or "").strip() for page in pdf.pages]
    except Exception:
        logger.debug("pdfplumber failed", exc_info=True)
        return None


def _read_with_pypdf(pdf_path: Path) -> list[str] | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(pdf_path))
        return [(page.extract_text() or "").strip() for page in reader.pages]
    except Exception:
        logger.debug("pypdf failed", exc_info=True)
        return None


def _enough_text(pages: list[str]) -> bool:
    return bool(pages) and sum(len(p) for p in pages) / len(pages) >= MIN_CHARS_PER_PAGE_THRESHOLD


# --------------------------------------------------------------------------
# Step 3: cleaning
# --------------------------------------------------------------------------

def remove_repeated_lines(pages: list[str]) -> list[str]:
    """Drops running headers/footers: short lines that repeat on many pages."""
    if len(pages) < 4:
        return pages

    def key(line: str) -> str:
        return re.sub(r"\d+", "#", line.strip().lower())

    counts: Counter = Counter()
    for page in pages:
        for k in {key(line) for line in page.splitlines() if 3 <= len(line.strip()) <= 90}:
            counts[k] += 1
    limit = max(3, int(len(pages) * 0.4))
    repeated = {k for k, n in counts.items() if n >= limit and k.replace("#", "").strip()}
    cleaned = []
    for page in pages:
        keep = [line for line in page.splitlines() if key(line) not in repeated]
        cleaned.append("\n".join(keep))
    return cleaned


_WATERMARK_RE = re.compile(r"^\s*arXiv:\S+\s+\[[^\]]+\]\s+\d{1,2}\s+\w+\s+\d{4}\s*$", re.MULTILINE)


def fix_hyphenation(text: str) -> str:
    """Joins words split across lines: 'auto-\\ncoders' -> 'autoencoders'."""
    return re.sub(r"([a-z])-\n([a-z])", r"\1\2", text)


def normalize_text(text: str) -> str:
    """Turns ligatures (fi, fl) into normal letters and removes the arXiv side stamp."""
    text = unicodedata.normalize("NFKC", text)
    return _WATERMARK_RE.sub("", text)


def find_figure_captions(text: str) -> list[str]:
    captions = []
    for line in text.splitlines():
        if _CAPTION_RE.match(line) and len(line.strip()) > 12:
            captions.append(line.strip()[:300])
    return captions


# --------------------------------------------------------------------------
# Public function
# --------------------------------------------------------------------------

def extract_text(pdf_path: Path) -> ExtractedDocument:
    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.warning("Failed to open PDF %s: %s", pdf_path, exc)
        raise PdfExtractionError(f"Could not open PDF: {pdf_path}") from exc

    pages: list[str] = []
    tables: list[str] = []
    image_count = 0
    method = "pymupdf"
    try:
        for page in doc:
            page_text, page_tables, n_images = _read_page_pymupdf(page)
            pages.append(page_text.strip())
            tables.extend(page_tables)
            image_count += n_images
    except Exception as exc:
        logger.warning("PyMuPDF failed while reading %s: %s", pdf_path, exc)
        pages = []
    finally:
        doc.close()

    if not _enough_text(pages):
        for name, reader in (("pdfplumber", _read_with_pdfplumber), ("pypdf", _read_with_pypdf)):
            fallback = reader(pdf_path)
            if fallback and _enough_text(fallback):
                logger.info("Used %s fallback for %s", name, pdf_path)
                pages, method = fallback, name
                break

    page_count = len(pages)
    pages = [normalize_text(fix_hyphenation(p)) for p in remove_repeated_lines(pages)]
    full_text = "\n\n".join(pages)

    if page_count == 0 or (len(full_text) / max(page_count, 1)) < MIN_CHARS_PER_PAGE_THRESHOLD:
        logger.info(
            "PDF %s looks scanned/image-only (%d pages, %d chars total)",
            pdf_path, page_count, len(full_text),
        )
        raise ScannedPdfError(
            f"PDF appears to have no extractable text layer (likely scanned): {pdf_path}"
        )

    return ExtractedDocument(
        full_text=full_text,
        page_count=page_count,
        pages=pages,
        tables=tables,
        figure_captions=find_figure_captions(full_text),
        image_count=image_count,
        method=method,
    )


# --------------------------------------------------------------------------
# Abstract finder (used by the summarizer)
# --------------------------------------------------------------------------

_ABSTRACT_START = re.compile(r"\babstract\b\s*[-—–:.]*\s*", re.IGNORECASE)
_ABSTRACT_END = re.compile(
    r"\n\s*(index terms|keywords?|key words|ccs concepts|1\.?\s+introduction|i\.\s+introduction|introduction)\b",
    re.IGNORECASE,
)


def find_abstract(text: str, max_chars: int = 2500) -> str | None:
    """
    Finds the abstract in the first part of a paper's text.
    Returns None if no clear abstract is found (the caller then uses the
    abstract that came from the search source).
    """
    head = text[:7000]
    start = _ABSTRACT_START.search(head)
    if not start:
        return None
    body = head[start.end():]
    end = _ABSTRACT_END.search(body)
    abstract = body[: end.start()] if end else body[:max_chars]
    abstract = re.sub(r"\s*\n\s*", " ", abstract)
    abstract = re.sub(r"\s{2,}", " ", abstract).strip()
    if len(abstract) < 200:
        return None
    return abstract[:max_chars]
