import pytest

from app.api import agent as agent_api
from app.schemas.agent import AgentRunRequest
from app.services import job_store


class FakeGraph:
    async def astream(self, state, stream_mode):
        assert stream_mode == "updates"
        yield {"search": {"candidate_papers": [1, 2]}}
        yield {"domain": {"detected_field": "Computer Science"}}


@pytest.mark.asyncio
async def test_run_agent_job_records_steps_and_result(monkeypatch):
    monkeypatch.setattr(agent_api, "get_agent_graph", lambda: FakeGraph())
    job_id = job_store.create_job()
    await agent_api._run_agent_job(job_id, AgentRunRequest(topic="graph", field="Computer Science"), "u1")

    job = job_store.get_job(job_id)
    assert job["status"] == job_store.JobStatus.DONE
    assert job["steps_done"] == ["search", "domain"]
    assert job["result"]["detected_field"] == "Computer Science"
    assert job["result"]["user_field"] == "Computer Science"


@pytest.mark.asyncio
async def test_run_agent_job_failure_is_recorded(monkeypatch):
    class Broken:
        async def astream(self, state, stream_mode):
            raise RuntimeError("boom")
            yield  # pragma: no cover

    monkeypatch.setattr(agent_api, "get_agent_graph", lambda: Broken())
    job_id = job_store.create_job()
    await agent_api._run_agent_job(job_id, AgentRunRequest(topic="graph"), "u1")
    assert job_store.get_job(job_id)["status"] == job_store.JobStatus.FAILED
