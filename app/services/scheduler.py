import json
import logging
from typing import Any, Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.database import session_scope
from app.models import ScheduleJob
from app.services import leaderboard as leaderboard_service
from app.services import task_queue

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
        refresh_jobs()
        logger.info("Scheduler started")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler stopped")


def refresh_jobs() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.remove_all_jobs()
    with session_scope() as session:
        jobs = session.query(ScheduleJob).filter(ScheduleJob.enabled == 1).all()
    for job in jobs:
        try:
            trigger = CronTrigger.from_crontab(job.cron)
            _scheduler.add_job(run_schedule_job, trigger=trigger, args=[job.id], id=str(job.id), replace_existing=True)
        except Exception as exc:
            logger.error("Failed to schedule job %s: %s", job.name, exc)


def run_schedule_job(job_id: int) -> None:
    with session_scope() as session:
        job = session.get(ScheduleJob, job_id)
        if not job:
            return
        payload: Dict[str, Any] = json.loads(job.payload or "{}")
    logger.info("Running schedule job %s (%s)", job.name, job.job_type)
    if job.job_type == "leaderboard_run_all":
        leaderboard_service.run_all_leaderboards()
    elif job.job_type == "wallet_sync":
        address = payload.get("address")
        if address:
            task_queue.enqueue_wallet_sync(address)
    else:
        logger.warning("Unknown job type %s", job.job_type)


def create_schedule(name: str, job_type: str, cron: str, payload: Dict[str, Any] | None = None, enabled: bool = True) -> ScheduleJob:
    with session_scope() as session:
        job = ScheduleJob(name=name, job_type=job_type, cron=cron, payload=json.dumps(payload) if payload else None, enabled=1 if enabled else 0)
        session.add(job)
        session.flush()
        session.refresh(job)
    refresh_jobs()
    return job


def list_schedules():
    with session_scope() as session:
        return session.query(ScheduleJob).all()
