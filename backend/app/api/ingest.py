from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.ingest import IngestRequest, IngestResponse
from ingestion.pipeline import ingest_paper

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit(settings.rate_limit_default)
async def ingest(request: Request, payload: IngestRequest) -> IngestResponse:
    """
    Downloads and processes a paper's PDF into searchable chunks.
    Idempotent: re-ingesting the same paper is a fast no-op unless
    force=true is passed.
    """
    result = await ingest_paper(payload.paper, force=payload.force)
    return IngestResponse(**result)