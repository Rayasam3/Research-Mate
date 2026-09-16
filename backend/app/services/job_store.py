"""
Simple in-memory job tracker for agent runs. A process-local dict is
enough for local development with one uvicorn worker; Phase 7/8 swaps
this for Redis-backed job tracking once the app needs to run across
multiple processes/instances for real public traffic.
"""
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_jobs: dict[str, dict[str, Any]] = {}


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


def create_job() -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": JobStatus.QUEUED,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None,
    }
    return job_id


def set_running(job_id: str) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = JobStatus.RUNNING


def set_done(job_id: str, result: dict) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = JobStatus.DONE
        _jobs[job_id]["result"] = result


def set_failed(job_id: str, error: str) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = JobStatus.FAILED
        _jobs[job_id]["error"] = error


def get_job(job_id: str) -> dict | None:
    return _jobs.get(job_id)