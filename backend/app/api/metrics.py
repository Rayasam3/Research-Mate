from fastapi import APIRouter

from app.services.metrics import get_metrics_snapshot

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Basic operational metrics: uptime, request/failure counts per
    endpoint, and LLM call latency. Not authenticated - fine for local
    dev and low-stakes deployment; consider gating this behind auth or an
    internal-only network before wide public exposure.
    """
    return get_metrics_snapshot()