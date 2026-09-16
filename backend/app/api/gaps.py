from fastapi import APIRouter, Query, Request

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
) -> GapAnalysisResponse:
    """
    Finds methods/datasets used in only one of the given papers (a real,
    grounded signal of under-exploration), and asks the LLM to phrase
    these as plain-English gap statements.
    """
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    result = await analyze_gaps(ids)
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