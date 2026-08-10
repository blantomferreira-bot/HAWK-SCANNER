import asyncio
import logging

from hawk_scheduler.main import run_job_safely


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
