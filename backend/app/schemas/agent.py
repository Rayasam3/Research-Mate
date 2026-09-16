from pydantic import BaseModel, Field

from app.services.job_store import JobStatus


class AgentRunRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=300)
    max_papers: int = Field(default=5, ge=1, le=20)
    year_from: int | None = None
    year_to: int | None = None


class AgentRunResponse(BaseModel):
    job_id: str
    status: JobStatus


class AgentStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    result: dict | None = None
    error: str | None = None