import asyncio
import logging
import os
import re
from collections.abc import Callable, Coroutine
from typing import Any

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from hawk_scheduler.config import daily_learning_hour_utc, scan_interval_minutes

logger = logging.getLogger(__name__)

_WORKER_URL_PATTERN = re.compile(r"^(https?://[A-Za-z0-9.-]+(?::\d{1,5})?)")


def worker_base_url() -> str:
    """Return the internal worker URL, rejecting malformed configuration early.

    Railway environment-variable interpolation is occasionally pasted together
    with the next variable.  Keeping the valid URL prefix prevents that
    configuration typo from disabling every scheduled scan, while malformed
    values still fail with an actionable error.
    """
    raw_value = os.getenv("WORKER_URL", "http://worker:8001").strip()
    match = _WORKER_URL_PATTERN.match(raw_value)
    if match is None:
        raise ValueError("WORKER_URL must start with an http(s) worker URL")
    return match.group(1).rstrip("/")


async def trigger_scan() -> None:
    worker_url = worker_base_url()
    token = os.getenv("INTERNAL_SCHEDULER_TOKEN", "")
    if not token:
        raise RuntimeError("INTERNAL_SCHEDULER_TOKEN is required")
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(f"{worker_url}/internal/scanner/run", headers={"X-Scheduler-Token": token})
        response.raise_for_status()


async def trigger_daily_learning() -> None:
    worker_url = worker_base_url()
    token = os.getenv("INTERNAL_SCHEDULER_TOKEN", "")
    if not token:
        raise RuntimeError("INTERNAL_SCHEDULER_TOKEN is required")
    async with httpx.AsyncClient(timeout=1800) as client:
        response = await client.post(f"{worker_url}/internal/ml/train", headers={"X-Scheduler-Token": token})
        response.raise_for_status()


async def run_job_safely(name: str, job: Callable[[], Coroutine[Any, Any, None]]) -> bool:
    """Keep the scheduler process alive when an upstream source is temporarily unavailable."""
    try:
        await job()
    except Exception:
        logger.exception("Scheduler job failed", extra={"job": name})
        return False
    return True


async def main() -> None:
    interval = scan_interval_minutes()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_job_safely,
        IntervalTrigger(minutes=interval),
        args=("scan", trigger_scan),
        id="hawk-scan",
        max_instances=1,
        coalesce=True,
    )
    learning_hour = daily_learning_hour_utc()
    scheduler.add_job(
        run_job_safely,
        CronTrigger(hour=learning_hour, minute=0),
        args=("daily_learning", trigger_daily_learning),
        id="hawk-ml-training",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    await run_job_safely("scan", trigger_scan)  # First scan starts immediately; subsequent scans run every ten minutes.
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
