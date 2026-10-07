from fastapi import APIRouter, Depends, Query, Request

from app.api.auth import get_current_user
from app.db.models import User

from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.gaps import (
    DraftRelatedWorkRequest,
    DraftRelatedWorkResponse,
    GapAnalysisResponse,
)
from app.services.gap_analysis import analyze_gaps
from app.services.related_work import build_related_work_draft

router = APIRouter()


@router.get("/gaps", response_model=GapAnalysisResponse)
@limiter.limit(settings.rate_limit_default)
async def get_gaps(
    request: Request,
    paper_ids: str = Query(..., description="Comma-separated paper_ids to analyze"),
    user: User = Depends(get_current_user),
) -> GapAnalysisResponse:
    """
    Research-gap CANDIDATES with evidence: (1) method x dataset pairs that no
    paper has tried, (2) limitations and future work the authors wrote.
    """
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    result = await analyze_gaps(ids, user.id)
    return GapAnalysisResponse(**result)


@router.post("/draft-related-work", response_model=DraftRelatedWorkResponse)
@limiter.limit(settings.rate_limit_default)
async def draft_related_work(request: Request, payload: DraftRelatedWorkRequest) -> DraftRelatedWorkResponse:
    """
    Synthesizes cached summaries for the given papers into one Related
    Work paragraph with inline citations, plus a BibTeX reference list.
    Papers without a cached summary yet are skipped and reported.
    """
    result = await build_related_work_draft(payload.paper_ids)
    return DraftRelatedWorkResponse(**result)