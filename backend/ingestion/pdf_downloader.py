"""
Downloads a paper's PDF to disk. Retries transient failures (timeouts,
5xx errors) with exponential backoff; gives up cleanly on permanent
failures (404, no URL) so the pipeline can report a real reason rather
than hanging or crashing.
"""
import logging
from pathlib import Path

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings

logger = logging.getLogger(__name__)


class PdfDownloadError(Exception):
    """Raised when a PDF could not be downloaded after all retries."""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    reraise=True,
)
async def _download_with_retry(url: str, dest_path: Path) -> None:
    async with httpx.AsyncClient(
        timeout=settings.pdf_download_timeout_seconds, follow_redirects=True
    ) as client:
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in resp.aiter_bytes():
                    f.write(chunk)


async def download_pdf(pdf_url: str, dest_path: Path) -> None:
    """
    Downloads pdf_url to dest_path. Raises PdfDownloadError on failure -
    callers should catch this and record it as an ingestion-status reason,
    not let it crash the whole ingest request.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        await _download_with_retry(pdf_url, dest_path)
    except Exception as exc:
        logger.warning("PDF download failed for url=%s: %s", pdf_url, exc)
        # Clean up a partially-written file so it's never mistaken for a
        # successfully cached PDF later.
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)
        raise PdfDownloadError(f"Could not download PDF from {pdf_url}") from exc