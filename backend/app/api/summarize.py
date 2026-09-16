from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.summary import SummarizeRequest, SummarizeResponse
from app.services.summarizer import summarize_paper

router = APIRouter()


@router.post("/summarize/{paper_id}", response_model=SummarizeResponse)
@limiter.limit(settings.rate_limit_default)
async def summarize(request: Request, paper_id: str, payload: SummarizeRequest) -> SummarizeResponse:
    """
    Generates a plain-English summary card for an already-ingested paper.
    Idempotent: re-requesting the same paper's summary is a fast no-op
    unless force=true is passed.
    """
    result = await summarize_paper(paper_id, force=payload.force)
    return SummarizeResponse(**result)