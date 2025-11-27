import logging
from typing import Any, Dict, Optional

from rq import Queue
from rq.job import Job
from redis import Redis

from app.core.config import get_settings
from app.services import etl, scoring, ai as ai_service
from app.services import tasks_service
from app.services import notifications as notification_service
from app.services import processing

logger = logging.getLogger(__name__)


PROCESSING_QUEUE = "wallet-processing"


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue(PROCESSING_QUEUE, connection=redis, default_timeout=600)


def enqueue_wallet_sync(address: str, end_time: int | None = None, scheduled_by: str = "manual", force: bool = False) -> str:
    log_id = processing.prepare_stage(
        address, "sync", payload={"end_time": end_time}, scheduled_by=scheduled_by, force=force
    )
    q = get_queue()
    job: Job = q.enqueue(run_wallet_sync, address, end_time, log_id, scheduled_by)
    logger.info("Enqueued wallet sync", extra={"address": address, "job_id": job.id})
    return job.id


def enqueue_wallet_score(address: str, scheduled_by: str = "pipeline", force: bool = False) -> Optional[str]:
    try:
        log_id = processing.prepare_stage(address, "score", scheduled_by=scheduled_by, force=force)
    except ValueError:
        return None
    q = get_queue()
    job: Job = q.enqueue(run_wallet_score, address, log_id, scheduled_by)
    logger.info("Enqueued wallet score", extra={"address": address, "job_id": job.id})
    return job.id


def enqueue_wallet_ai(address: str, scheduled_by: str = "pipeline", force: bool = False) -> Optional[str]:
    try:
        log_id = processing.prepare_stage(address, "ai", scheduled_by=scheduled_by, force=force)
    except ValueError:
        return None
    q = get_queue()
    job: Job = q.enqueue(run_wallet_ai, address, log_id, scheduled_by)
    logger.info("Enqueued wallet AI", extra={"address": address, "job_id": job.id})
    return job.id


def run_wallet_sync(address: str, end_time: int | None = None, log_id: int | None = None, scheduled_by: str = "system") -> Dict[str, Any]:
    """Full data sync followed by automatic score enqueue."""
    if log_id is None:
        log_id = processing.prepare_stage(
            address, "sync", payload={"end_time": end_time}, scheduled_by=scheduled_by, force=True
        )
    processing.mark_stage_running(log_id)
    task_id = tasks_service.log_task_start("wallet_sync", {"address": address, "end_time": end_time, "scheduled_by": scheduled_by})
    try:
        ledger = etl.sync_ledger(address, end_time=end_time)
        fills = etl.sync_fills(address, end_time=end_time)
        funding = etl.sync_funding(address, end_time=end_time)
        etl.sync_user_fees(address)
        positions = etl.sync_positions(address)
        orders = etl.sync_orders(address)
        portfolio_points = etl.sync_portfolio_series(address)
        result = {
            "fills": fills,
            "ledger": ledger,
            "funding": funding,
            "positions": positions,
            "orders": orders,
            "portfolio_points": portfolio_points,
        }
        processing.mark_stage_success(log_id, result)
        tasks_service.log_task_end(task_id, "completed", result=result)
        enqueue_wallet_score(address, scheduled_by="pipeline")
        return result
    except Exception as exc:
        processing.mark_stage_failure(log_id, str(exc))
        tasks_service.log_task_end(task_id, "failed", error=str(exc))
        _notify_failure(address, exc)
        raise


def run_wallet_score(address: str, log_id: int | None = None, scheduled_by: str = "system") -> Dict[str, Any]:
    if log_id is None:
        log_id = processing.prepare_stage(address, "score", scheduled_by=scheduled_by, force=True)
    processing.mark_stage_running(log_id)
    task_id = tasks_service.log_task_start("wallet_score", {"address": address, "scheduled_by": scheduled_by})
    try:
        metric, score = scoring.compute_metrics(address)
        result = {"metric_id": metric.id, "score_id": score.id}
        processing.mark_stage_success(log_id, result)
        tasks_service.log_task_end(task_id, "completed", result=result)
        enqueue_wallet_ai(address, scheduled_by="pipeline")
        return result
    except Exception as exc:
        processing.mark_stage_failure(log_id, str(exc))
        tasks_service.log_task_end(task_id, "failed", error=str(exc))
        _notify_failure(address, exc)
        raise


def run_wallet_ai(address: str, log_id: int | None = None, scheduled_by: str = "system") -> Dict[str, Any]:
    if log_id is None:
        log_id = processing.prepare_stage(address, "ai", scheduled_by=scheduled_by, force=True)
    processing.mark_stage_running(log_id)
    task_id = tasks_service.log_task_start("wallet_ai", {"address": address, "scheduled_by": scheduled_by})
    try:
        analysis = ai_service.analyze_wallet(address)
        result = {"analysis_id": analysis.id}
        processing.mark_stage_success(log_id, result)
        tasks_service.log_task_end(task_id, "completed", result=result)
        return result
    except Exception as exc:
        processing.mark_stage_failure(log_id, str(exc))
        tasks_service.log_task_end(task_id, "failed", error=str(exc))
        _notify_failure(address, exc)
        raise


def _notify_failure(address: str, exc: Exception) -> None:
    try:
        notification_service.send_notification(
            template_id=1,
            recipient=get_settings().smtp_from,
            payload={"wallet": address, "error": str(exc)},
        )
    except Exception:
        logger.warning("Failed to send failure notification", exc_info=True)
