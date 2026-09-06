"""
Semantic Scholar client. Works without an API key at low volume; set
SEMANTIC_SCHOLAR_API_KEY in .env to raise the rate limit.
Docs: https://api.semanticscholar.org/api-docs/graph
"""
import logging
from datetime import date

import httpx

from app.core.config import settings
from app.schemas.paper import Paper, PaperSource

logger = logging.getLogger(__name__)

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS = "title,authors,abstract,year,externalIds,openAccessPdf,url"


async def search_semantic_scholar(topic: str, max_results: int) -> list[Paper]:
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    params = {"query": topic, "limit": max_results, "fields": FIELDS}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("Semantic Scholar search failed for topic=%r", topic)
        return []

    results: list[Paper] = []
    for item in data.get("data", []):
        try:
            external_ids = item.get("externalIds") or {}
            open_access = item.get("openAccessPdf") or {}
            year = item.get("year")
            results.append(
                Paper(
                    external_id=item.get("paperId", ""),
                    source=PaperSource.SEMANTIC_SCHOLAR,
                    title=item.get("title") or "Untitled",
                    authors=[a.get("name", "") for a in item.get("authors") or []],
                    abstract=item.get("abstract"),
                    published_date=date(year, 1, 1) if year else None,
                    pdf_url=open_access.get("url"),
                    doi=external_ids.get("DOI"),
                    url=item.get("url"),
                )
            )
        except Exception:
            logger.exception("Failed to parse Semantic Scholar result: %r", item)
            continue

    return results
