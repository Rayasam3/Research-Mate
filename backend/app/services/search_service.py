"""
Fans a topic query out to all requested sources concurrently, merges the
results, and dedupes across sources (by DOI first, then normalized title).
"""
import asyncio
import re
from datetime import date

from app.core.config import settings
from app.schemas.paper import Paper, PaperSource
from app.services.arxiv_client import search_arxiv
from app.services.pubmed_client import search_pubmed
from app.services.semantic_scholar_client import search_semantic_scholar

_SOURCE_FUNCS = {
    PaperSource.ARXIV: search_arxiv,
    PaperSource.SEMANTIC_SCHOLAR: search_semantic_scholar,
    PaperSource.PUBMED: search_pubmed,
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


async def search_all_sources(
    topic: str,
    max_results: int | None = None,
    sources: list[PaperSource] | None = None,
) -> list[Paper]:
    per_source_cap = max_results or settings.search_max_results_per_source
    active_sources = sources or list(_SOURCE_FUNCS.keys())

    tasks = [_SOURCE_FUNCS[src](topic, per_source_cap) for src in active_sources]
    results_per_source = await asyncio.gather(*tasks)

    merged: list[Paper] = [paper for source_results in results_per_source for paper in source_results]
    deduped = _dedupe(merged)

    # Simple recency-first ordering as a first-pass ranking; relevance
    # scoring / better ranking is a candidate improvement for later phases.
    deduped.sort(key=lambda p: p.published_date or date.min, reverse=True)

    return deduped
