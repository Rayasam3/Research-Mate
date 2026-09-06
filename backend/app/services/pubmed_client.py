"""
PubMed client via NCBI E-utilities (esearch + esummary). No full-text/PDF
is available here — PubMed indexes biomedical literature abstracts, and a
real PDF link (when it exists at all) is added in Phase 2 via DOI resolution.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
"""
import logging
from datetime import date

import httpx

from app.core.config import settings
from app.schemas.paper import Paper, PaperSource

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def _common_params() -> dict:
    params = {"db": "pubmed", "retmode": "json"}
    if settings.pubmed_email:
        params["email"] = settings.pubmed_email
    if settings.pubmed_api_key:
        params["api_key"] = settings.pubmed_api_key
    return params


def _parse_pub_date(pubdate_raw: str) -> date | None:
    # PubMed dates are inconsistently formatted ("2023 Jun", "2023", "2023 Jun 12").
    parts = pubdate_raw.split()
    try:
        year = int(parts[0])
        return date(year, 1, 1)
    except (ValueError, IndexError):
        return None


async def search_pubmed(topic: str, max_results: int) -> list[Paper]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            search_resp = await client.get(
                ESEARCH_URL,
                params={**_common_params(), "term": topic, "retmax": max_results},
            )
            search_resp.raise_for_status()
            id_list = search_resp.json().get("esearchresult", {}).get("idlist", [])

            if not id_list:
                return []

            summary_resp = await client.get(
                ESUMMARY_URL,
                params={**_common_params(), "id": ",".join(id_list)},
            )
            summary_resp.raise_for_status()
            summary_data = summary_resp.json().get("result", {})
    except Exception:
        logger.exception("PubMed search failed for topic=%r", topic)
        return []

    results: list[Paper] = []
    for pmid in id_list:
        item = summary_data.get(pmid)
        if not item:
            continue
        try:
            authors = [a.get("name", "") for a in item.get("authors") or []]
            doi = next(
                (idobj.get("value") for idobj in item.get("articleids", []) if idobj.get("idtype") == "doi"),
                None,
            )
            results.append(
                Paper(
                    external_id=pmid,
                    source=PaperSource.PUBMED,
                    title=item.get("title") or "Untitled",
                    authors=authors,
                    abstract=None,  # esummary doesn't include abstracts; efetch needed for that (Phase 2)
                    published_date=_parse_pub_date(item.get("pubdate", "")),
                    pdf_url=None,
                    doi=doi,
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                )
            )
        except Exception:
            logger.exception("Failed to parse PubMed result for pmid=%s", pmid)
            continue

    return results
