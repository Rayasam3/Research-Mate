"""
Fans a topic query out to all requested sources concurrently, merges the
results, dedupes across sources (by DOI first, then normalized title),
optionally filters by year range, and caches the final result so repeated
identical searches don't re-hit rate-limited external APIs.
"""
import asyncio
import re
from datetime import date
import logging

logger = logging.getLogger(__name__)


from app.core.config import settings
from app.schemas.paper import Paper, PaperSource
from app.services.arxiv_client import search_arxiv
from app.services.openalex_client import search_openalex
from app.services.pubmed_client import search_pubmed
from app.services.search_cache import get_cached_search, set_cached_search
from app.services.semantic_scholar_client import search_semantic_scholar

_SOURCE_FUNCS = {
    PaperSource.ARXIV: search_arxiv,
    PaperSource.SEMANTIC_SCHOLAR: search_semantic_scholar,
    PaperSource.PUBMED: search_pubmed,
    PaperSource.OPENALEX: search_openalex,
}


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())


def _dedupe(papers: list[Paper]) -> list[Paper]:
    seen_dois: set[str] = set()
    seen_titles: set[str] = set()
    deduped: list[Paper] = []

    for paper in papers:
        doi_key = paper.doi.lower().strip() if paper.doi else None
        title_key = _normalize_title(paper.title)

        if doi_key and doi_key in seen_dois:
            continue
        if title_key and title_key in seen_titles:
            continue

        if doi_key:
            seen_dois.add(doi_key)
        seen_titles.add(title_key)
        deduped.append(paper)

    return deduped


def _filter_by_year(papers: list[Paper], year_from: int | None, year_to: int | None) -> list[Paper]:
    if year_from is None and year_to is None:
        return papers

    filtered = []
    for paper in papers:
        if paper.published_date is None:
            continue  # can't verify it's in range, so exclude rather than guess
        year = paper.published_date.year
        if year_from is not None and year < year_from:
            continue
        if year_to is not None and year > year_to:
            continue
        filtered.append(paper)
    return filtered


async def search_all_sources(
    topic: str,
    max_results: int | None = None,
    sources: list[PaperSource] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[Paper]:
    per_source_cap = max_results or settings.search_max_results_per_source
    active_sources = sources or list(_SOURCE_FUNCS.keys())
    source_names = [s.value for s in active_sources]

    cached = await get_cached_search(topic, source_names, per_source_cap, year_from, year_to)
    if cached is not None:
        return [Paper(**p) for p in cached]

    tasks = [_SOURCE_FUNCS[src](topic, per_source_cap) for src in active_sources]
    results_per_source = await asyncio.gather(*tasks)

    merged: list[Paper] = [paper for source_results in results_per_source for paper in source_results]
    deduped = _dedupe(merged)
    filtered = _filter_by_year(deduped, year_from, year_to)

    # Simple recency-first ordering as a first-pass ranking; relevance
    # scoring / better ranking is a candidate improvement for later phases.
    filtered.sort(key=lambda p: p.published_date or date.min, reverse=True)

    await set_cached_search(
        topic, source_names, per_source_cap, year_from, year_to, [p.model_dump(mode="json") for p in filtered]
    )
    logger.info(
    "Search completed: topic=%r sources=%s results=%d",
    topic, source_names, len(filtered),
    )
    return filtered