from fastapi import APIRouter, Depends, Request

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.ingest import IngestRequest, IngestResponse
from ingestion.pipeline import ingest_paper

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit(settings.rate_limit_default)
async def ingest(
    request: Request, payload: IngestRequest, user: User = Depends(get_current_user)
) -> IngestResponse:
    """
    Downloads and processes a paper's PDF into searchable chunks.
    Requires login. Idempotent: re-ingesting the same paper is a fast
    no-op unless force=true is passed.
    """
    result = await ingest_paper(payload.paper, force=payload.force)
    return IngestResponse(**result)