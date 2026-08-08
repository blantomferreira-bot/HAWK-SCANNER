import asyncio
import os

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from hawk_scheduler.config import daily_learning_hour_utc, scan_interval_minutes


async def trigger_scan() -> None:
    worker_url = os.getenv("WORKER_URL", "http://worker:8001").rstrip("/")
    token = os.getenv("INTERNAL_SCHEDULER_TOKEN", "")
    if not token:
        raise RuntimeError("INTERNAL_SCHEDULER_TOKEN is required")
    async with httpx.AsyncClient(timeout=600) as client:
        response = await client.post(f"{worker_url}/internal/scanner/run", headers={"X-Scheduler-Token": token})
        response.raise_for_status()


async def trigger_daily_learning() -> None:
    worker_url = os.getenv("WORKER_URL", "http://worker:8001").rstrip("/")
    token = os.getenv("INTERNAL_SCHEDULER_TOKEN", "")
    if not token:
        raise RuntimeError("INTERNAL_SCHEDULER_TOKEN is required")
    async with httpx.AsyncClient(timeout=1800) as client:
        response = await client.post(f"{worker_url}/internal/ml/train", headers={"X-Scheduler-Token": token})
        response.raise_for_status()


async def main() -> None:
    interval = scan_interval_minutes()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(trigger_scan, IntervalTrigger(minutes=interval), id="hawk-scan", max_instances=1, coalesce=True)
    learning_hour = daily_learning_hour_utc()
    scheduler.add_job(trigger_daily_learning, CronTrigger(hour=learning_hour, minute=0), id="hawk-ml-training", max_instances=1, coalesce=True)
    scheduler.start()
    await trigger_scan()  # First scan starts immediately; subsequent scans run every ten minutes.
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
