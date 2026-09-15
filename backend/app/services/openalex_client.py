"""
OpenAlex client. Fully free, no API key required, and far more generous
rate limits than ArXiv/Semantic Scholar (100,000 requests/day per the
"polite pool" - unlocked just by sending a contact email, no signup).
Docs: https://docs.openalex.org/api-entities/works/search-works
"""
import logging
from datetime import date

import httpx

from app.core.config import settings
from app.schemas.paper import Paper, PaperSource

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openalex.org/works"


def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """
    OpenAlex stores abstracts as an inverted index (word -> [positions])
    instead of plain text, to keep response payloads small. This turns it
    back into a normal, readable string.
    """
    if not inverted_index:
        return None
    positions: dict[int, str] = {}
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions[idx] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions))


async def search_openalex(topic: str, max_results: int) -> list[Paper]:
    params = {
        "search": topic,
        "per_page": max_results,
        # The "polite pool" gets much higher rate limits - just requires
        # identifying yourself via a mailto param, no registration needed.
        "mailto": settings.pubmed_email or "researchmate@example.com",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        logger.exception("OpenAlex search failed for topic=%r", topic)
        return []

    results: list[Paper] = []
    for item in data.get("results", []):
        try:
            year = item.get("publication_year")
            open_access = item.get("open_access") or {}
            authorships = item.get("authorships") or []
            results.append(
                Paper(
                    external_id=item.get("id", "").rsplit("/", 1)[-1],
                    source=PaperSource.OPENALEX,
                    title=item.get("title") or item.get("display_name") or "Untitled",
                    authors=[
                        a.get("author", {}).get("display_name", "")
                        for a in authorships
                        if a.get("author")
                    ],
                    abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
                    published_date=date(year, 1, 1) if year else None,
                    pdf_url=open_access.get("oa_url"),
                    doi=(item.get("doi") or "").replace("https://doi.org/", "") or None,
                    url=item.get("id"),
                )
            )
        except Exception:
            logger.exception("Failed to parse OpenAlex result: %r", item)
            continue

    return results