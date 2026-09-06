from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.paper import SearchRequest, SearchResponse
from app.services.search_service import search_all_sources

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
@limiter.limit(settings.rate_limit_search)
async def search_papers(request: Request, payload: SearchRequest) -> SearchResponse:
    """
    Search ArXiv, Semantic Scholar, and PubMed for a topic, merge and
    dedupe the results. Rate-limited since this is a public endpoint.
    """
    results = await search_all_sources(
        topic=payload.topic,
        max_results=payload.max_results,
        sources=payload.sources,
    )
    return SearchResponse(topic=payload.topic, total_results=len(results), results=results)
