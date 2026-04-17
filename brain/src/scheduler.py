"""APScheduler setup for consolidation, decay, and routine triggers."""

from __future__ import annotations

from typing import Any

from brain.src.logger import get_logger

log = get_logger("scheduler")

_scheduler: Any = None


async def init_scheduler(brain_manager: Any, interval_hours: int = 6) -> None:
    """Initialize APScheduler with consolidation and decay jobs."""
    global _scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        log.warning("apscheduler_not_installed", message="Scheduled tasks disabled")
        return

    _scheduler = AsyncIOScheduler()

    # Consolidation job
    _scheduler.add_job(
        _run_consolidation,
        trigger=IntervalTrigger(hours=interval_hours),
        kwargs={"brain": brain_manager},
        id="consolidation",
        name="Memory Consolidation",
        replace_existing=True,
    )

    # Decay job (daily)
    _scheduler.add_job(
        _run_decay,
        trigger=IntervalTrigger(hours=24),
        kwargs={"brain": brain_manager},
        id="decay",
        name="Memory Decay",
        replace_existing=True,
    )

    _scheduler.start()
    log.info("scheduler_started", consolidation_interval=f"{interval_hours}h", decay_interval="24h")


async def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        log.info("scheduler_stopped")


async def _run_consolidation(brain: Any) -> None:
    try:
        stats = await brain.consolidate()
        log.info("scheduled_consolidation_complete", **stats)
    except Exception as e:
        log.error("scheduled_consolidation_failed", error=str(e))


async def _run_decay(brain: Any) -> None:
    try:
        from brain.src.cognitive.decay import process_decay
        stats = await process_decay()
        log.info("scheduled_decay_complete", **stats)
    except Exception as e:
        log.error("scheduled_decay_failed", error=str(e))
