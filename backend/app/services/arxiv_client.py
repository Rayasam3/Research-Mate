"""
ArXiv client. Uses the `arxiv` package, which wraps ArXiv's public API
(no API key required).
"""
import logging

import arxiv

from app.schemas.paper import Paper, PaperSource

logger = logging.getLogger(__name__)


async def search_arxiv(topic: str, max_results: int) -> list[Paper]:
    try:
        client = arxiv.Client(delay_seconds=3.0, num_retries=1)
        search = arxiv.Search(
            query=topic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
        )
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
                )
            )
        return results
    except Exception:
        # A single source failing should never take down the whole search.
        logger.exception("ArXiv search failed for topic=%r", topic)
        return []
