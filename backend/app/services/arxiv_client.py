"""
ArXiv client. Uses the `arxiv` package (public API, no key needed).

The `arxiv` package is synchronous and can be slow, so it runs in a worker
thread with a time limit. Without this it froze the whole server while
waiting for ArXiv.
"""
import asyncio
import logging

import arxiv

from app.schemas.paper import Paper, PaperSource
from app.services.domain import field_from_arxiv_category

logger = logging.getLogger(__name__)

ARXIV_TIMEOUT_SECONDS = 30


def _search_arxiv_blocking(topic: str, max_results: int) -> list[Paper]:
    client = arxiv.Client(delay_seconds=3.0, num_retries=1)
    search = arxiv.Search(query=topic, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    results: list[Paper] = []
    for entry in client.results(search):
        results.append(
            Paper(
                external_id=entry.get_short_id(),
                source=PaperSource.ARXIV,
                title=entry.title.strip().replace("\n", " "),
                authors=[a.name for a in entry.authors],
                abstract=entry.summary.strip().replace("\n", " ") if entry.summary else None,
                published_date=entry.published.date() if entry.published else None,
                pdf_url=entry.pdf_url,
                doi=entry.doi,
                url=entry.entry_id,
                field=field_from_arxiv_category(entry.primary_category),
            )
        )
    return results


async def search_arxiv(topic: str, max_results: int) -> list[Paper]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search_arxiv_blocking, topic, max_results),
            timeout=ARXIV_TIMEOUT_SECONDS,
        )
    except Exception:
        # One source failing must never take down the whole search.
        logger.exception("ArXiv search failed for topic=%r", topic)
        return []
