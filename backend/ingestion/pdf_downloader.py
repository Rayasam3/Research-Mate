"""
Downloads a paper's PDF to disk and checks that it really is a PDF.

Many "PDF links" from OpenAlex / Semantic Scholar are really web pages
(a publisher landing page). Saving that as a .pdf gives a broken file, so:
  1. we send a normal browser User-Agent (some sites block plain scripts),
  2. we check the file starts with "%PDF",
  3. if we got an HTML page instead, we look inside it for the real PDF
     link (the standard `citation_pdf_url` tag, or a link ending in .pdf)
     and try that once.
Transient errors (timeouts, 5xx, 429) are retried; permanent ones (404,
403) are not.
"""
import logging
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html;q=0.8,*/*;q=0.5",
}

_META_PDF_RE = re.compile(
    r"""<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["']([^"']+)["']""", re.IGNORECASE
)
_META_PDF_RE_REVERSED = re.compile(
    r"""<meta[^>]+content=["']([^"']+)["'][^>]+name=["']citation_pdf_url["']""", re.IGNORECASE
)
_PDF_LINK_RE = re.compile(r"""href=["']([^"']+?\.pdf(?:\?[^"']*)?)["']""", re.IGNORECASE)


class PdfDownloadError(Exception):
    """Raised when a real PDF could not be downloaded."""


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code == 429 or code >= 500
    return isinstance(exc, httpx.TransportError)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _fetch(url: str) -> bytes:
    async with httpx.AsyncClient(
        timeout=settings.pdf_download_timeout_seconds, follow_redirects=True, headers=_HEADERS
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def is_pdf_bytes(data: bytes) -> bool:
    """A real PDF starts with '%PDF' (allowing a few junk bytes before it)."""
    return b"%PDF" in data[:1024]


def find_pdf_link(html: str, base_url: str) -> str | None:
    """Looks inside a web page for the link to the real PDF."""
    for pattern in (_META_PDF_RE, _META_PDF_RE_REVERSED, _PDF_LINK_RE):
        match = pattern.search(html)
        if match:
            return urljoin(base_url, unescape(match.group(1)))
    return None


async def download_pdf(pdf_url: str, dest_path: Path) -> None:
    """
    Downloads pdf_url to dest_path. Raises PdfDownloadError if no real PDF
    could be obtained - callers record that as the reason for skipping
    the paper instead of crashing the whole run.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        data = await _fetch(pdf_url)

        if not is_pdf_bytes(data):
            # Probably a landing page: look for the real PDF link inside it.
            html = data[:500_000].decode("utf-8", errors="ignore")
            real_url = find_pdf_link(html, pdf_url)
            if not real_url or real_url == pdf_url:
                raise PdfDownloadError(f"The link is a web page, not a PDF: {pdf_url}")
            logger.info("Landing page %s -> trying %s", pdf_url, real_url)
            data = await _fetch(real_url)
            if not is_pdf_bytes(data):
                raise PdfDownloadError(f"No real PDF found behind: {pdf_url}")

        dest_path.write_bytes(data)
    except PdfDownloadError:
        dest_path.unlink(missing_ok=True)
        raise
    except Exception as exc:
        logger.warning("PDF download failed for url=%s: %s", pdf_url, exc)
        dest_path.unlink(missing_ok=True)
        raise PdfDownloadError(f"Could not download PDF from {pdf_url}") from exc
