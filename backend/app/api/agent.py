from fastapi import APIRouter, BackgroundTasks, Depends, Request

from agents.graph import get_agent_graph
from app.api.auth import get_current_user
from app.core.config import settings
from app.core.limiter import limiter
from app.db.models import User
from app.schemas.agent import AgentRunRequest, AgentRunResponse, AgentStatusResponse
from app.services.job_store import add_step_done, create_job, get_job, set_done, set_failed, set_running

router = APIRouter()


async def _run_agent_job(job_id: str, payload: AgentRunRequest, user_id: str) -> None:
    set_running(job_id)
    try:
        graph = get_agent_graph()
        final_state = {
            "topic": payload.topic,
            "max_papers": payload.max_papers,
            "year_from": payload.year_from,
            "year_to": payload.year_to,
            "user_id": user_id,
            "user_field": payload.field,
            "errors": [],
        }
        # Run the agent one step at a time so the frontend can show progress.
        async for update in graph.astream(dict(final_state), stream_mode="updates"):
            for step_name, changes in update.items():
                final_state.update(changes)
                add_step_done(job_id, step_name)
        set_done(job_id, final_state)
    except Exception as exc:
        set_failed(job_id, str(exc))


@router.post("/agent/run", response_model=AgentRunResponse)
@limiter.limit(settings.rate_limit_default)
async def run_agent(
    request: Request,
    payload: AgentRunRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> AgentRunResponse:
    """
    Kicks off the full search -> filter -> ingest -> summarize pipeline
    for a topic, unattended. Requires login - resulting Paper nodes in
    the graph are tagged with the logged-in user's id. Returns
    immediately with a job ID; poll /agent/status/{job_id} for progress.
    """
    job_id = create_job()
    background_tasks.add_task(_run_agent_job, job_id, payload, user.id)
    return AgentRunResponse(job_id=job_id, status="queued")


@router.get("/agent/status/{job_id}", response_model=AgentStatusResponse)
async def agent_status(job_id: str, user: User = Depends(get_current_user)) -> AgentStatusResponse:
    job = get_job(job_id)
    if job is None:
        return AgentStatusResponse(job_id=job_id, status="failed", error="Unknown job_id")
    return AgentStatusResponse(
        job_id=job_id,
        status=job["status"],
        result=job["result"],
        error=job["error"],
        steps_done=job["steps_done"],
    )