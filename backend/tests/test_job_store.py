from app.services import job_store
from app.services.job_store import JobStatus


def test_create_job_starts_queued():
    job_id = job_store.create_job()
    job = job_store.get_job(job_id)
    assert job["status"] == JobStatus.QUEUED
    assert job["result"] is None
    assert job["error"] is None


def test_set_running_updates_status():
    job_id = job_store.create_job()
    job_store.set_running(job_id)
    assert job_store.get_job(job_id)["status"] == JobStatus.RUNNING


def test_set_done_stores_result():
    job_id = job_store.create_job()
    job_store.set_done(job_id, {"topic": "test"})
    job = job_store.get_job(job_id)
    assert job["status"] == JobStatus.DONE
    assert job["result"] == {"topic": "test"}


def test_set_failed_stores_error():
    job_id = job_store.create_job()
    job_store.set_failed(job_id, "something broke")
    job = job_store.get_job(job_id)
    assert job["status"] == JobStatus.FAILED
    assert job["error"] == "something broke"


def test_get_unknown_job_returns_none():
    assert job_store.get_job("nonexistent-id") is None