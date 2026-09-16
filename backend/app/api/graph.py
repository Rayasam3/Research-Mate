from fastapi import APIRouter, HTTPException, Query, Request

from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.graph import ComparisonResponse, RelatedPapersResponse
from app.services.comparison import find_related_papers, get_comparison_table

router = APIRouter()


@router.get("/compare", response_model=ComparisonResponse)
@limiter.limit(settings.rate_limit_default)
async def compare_papers(
    request: Request,
    paper_ids: str = Query(..., description="Comma-separated paper_ids to compare"),
) -> ComparisonResponse:
    """
    Returns a comparison table (title, year, methods, datasets) for the
    given papers, built from the knowledge graph. Papers that were never
    summarized (so never graph-indexed) are simply omitted.
    """
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    rows = await get_comparison_table(ids)
    return ComparisonResponse(rows=rows)


@router.get("/graph/related", response_model=RelatedPapersResponse)
@limiter.limit(settings.rate_limit_default)
async def related_papers(
    request: Request,
    entity_type: str = Query(..., pattern="^(method|dataset)$"),
    entity_name: str = Query(...),
    exclude_paper_id: str | None = Query(default=None),
) -> RelatedPapersResponse:
    """
    Finds other papers connected to the same method or dataset, e.g.
    "what other papers used ImageNet?" or "what other papers used
    self-attention?".
    """
    results = await find_related_papers(entity_type, entity_name, exclude_paper_id)
    return RelatedPapersResponse(entity_type=entity_type, entity_name=entity_name, related_papers=results)