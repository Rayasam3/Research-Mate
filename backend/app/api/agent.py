from fastapi import APIRouter, BackgroundTasks, Request

from agents.graph import get_agent_graph
from app.core.config import settings
from app.core.limiter import limiter
from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatusResponse
from app.services.job_store import create_job, get_job, set_done, set_failed, set_running

router = APIRouter()


async def _run_agent_job(job_id: str, payload: AgentRunRequest) -> None:
    set_running(job_id)
    try:
        graph = get_agent_graph()
        final_state = await graph.ainvoke(
            {
                "topic": payload.topic,
                "max_papers": payload.max_papers,
                "year_from": payload.year_from,
                "year_to": payload.year_to,
                "errors": [],
            }
        )
        set_done(job_id, final_state)
    except Exception as exc:
        set_failed(job_id, str(exc))


@router.post("/agent/run", response_model=AgentRunResponse)
@limiter.limit(settings.rate_limit_default)
async def run_agent(request: Request, payload: AgentRunRequest, background_tasks: BackgroundTasks) -> AgentRunResponse:
    """
    Kicks off the full search -> filter -> ingest -> summarize pipeline
    for a topic, unattended. Returns immediately with a job ID; poll
    /agent/status/{job_id} for progress and results.
    """
    job_id = create_job()
    background_tasks.add_task(_run_agent_job, job_id, payload)
    return AgentRunResponse(job_id=job_id, status="queued")


@router.get("/agent/status/{job_id}", response_model=AgentStatusResponse)
async def agent_status(job_id: str) -> AgentStatusResponse:
    job = get_job(job_id)
    if job is None:
        return AgentStatusResponse(job_id=job_id, status="failed", error="Unknown job_id")
    return AgentStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job["result"],
        error=job["error"],
    )