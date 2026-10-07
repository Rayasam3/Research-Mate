from fastapi import APIRouter, Depends, Query, Request

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.graph import ComparisonResponse, GraphViewResponse, RelatedPapersResponse
from app.services.comparison import find_related_papers, get_comparison_table
from app.services.graph_view import get_graph_view

router = APIRouter()


def _split_ids(paper_ids: str) -> list[str]:
    return [pid.strip() for pid in paper_ids.split(",") if pid.strip()]


@router.get("/compare", response_model=ComparisonResponse)
@limiter.limit(settings.rate_limit_default)
async def compare_papers(
    request: Request,
    paper_ids: str = Query(..., description="Comma-separated paper_ids to compare"),
    user: User = Depends(get_current_user),
) -> ComparisonResponse:
    """Side-by-side comparison built from the knowledge graph (only your papers)."""
    rows = await get_comparison_table(_split_ids(paper_ids), user.id)
    return ComparisonResponse(rows=rows)


@router.get("/graph/view", response_model=GraphViewResponse)
@limiter.limit(settings.rate_limit_default)
async def graph_view(
    request: Request,
    paper_ids: str = Query(..., description="Comma-separated paper_ids to draw"),
    user: User = Depends(get_current_user),
) -> GraphViewResponse:
    """Nodes and links of the knowledge graph, for the Knowledge Graph tab."""
    return GraphViewResponse(**await get_graph_view(_split_ids(paper_ids), user.id))


@router.get("/graph/related", response_model=RelatedPapersResponse)
@limiter.limit(settings.rate_limit_default)
async def related_papers(
    request: Request,
    entity_type: str = Query(..., pattern="^(method|dataset)$"),
    entity_name: str = Query(...),
    exclude_paper_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
) -> RelatedPapersResponse:
    """Other papers that use the same method or dataset."""
    results = await find_related_papers(entity_type, entity_name, user.id, exclude_paper_id)
    return RelatedPapersResponse(entity_type=entity_type, entity_name=entity_name, related_papers=results)
