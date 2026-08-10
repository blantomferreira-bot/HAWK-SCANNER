import asyncio
import logging

from hawk_scheduler.main import run_job_safely, worker_base_url


def test_worker_base_url_preserves_valid_url(monkeypatch):
    monkeypatch.setenv("WORKER_URL", "https://hawk-worker.internal:8001")

    assert worker_base_url() == "https://hawk-worker.internal:8001"


def test_worker_base_url_recovers_from_concatenated_railway_variable(monkeypatch):
    monkeypatch.setenv("WORKER_URL", "http://hawk-worker.internal:8001DATABASE_URL=postgresql://ignored")

    assert worker_base_url() == "http://hawk-worker.internal:8001"


def test_scheduler_job_failure_is_contained(caplog):
    async def failing_job() -> None:
        raise RuntimeError("provider unavailable")

    with caplog.at_level(logging.ERROR):
        completed = asyncio.run(run_job_safely("scan", failing_job))

    assert completed is False
    assert "Scheduler job failed" in caplog.text


def test_scheduler_job_success_is_reported():
    async def successful_job() -> None:
        return None

    assert asyncio.run(run_job_safely("scan", successful_job)) is True
