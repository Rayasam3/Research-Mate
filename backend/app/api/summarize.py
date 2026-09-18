from fastapi import APIRouter, Depends, Request

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.summary import SummarizeRequest, SummarizeResponse
from app.services.summarizer import summarize_paper

router = APIRouter()


@router.post("/summarize/{paper_id}", response_model=SummarizeResponse)
@limiter.limit(settings.rate_limit_default)
async def summarize(
    request: Request,
    paper_id: str,
    payload: SummarizeRequest,
    user: User = Depends(get_current_user),
) -> SummarizeResponse:
    """
    Generates a plain-English summary card for an already-ingested paper.
    Requires login - the resulting Paper node in the graph is tagged with
    the logged-in user's id, so comparison/gaps queries can be scoped per
    user. Idempotent: re-requesting the same paper's summary is a fast
    no-op unless force=true is passed.
    """
    result = await summarize_paper(paper_id, force=payload.force, user_id=user.id)
    return SummarizeResponse(**result)