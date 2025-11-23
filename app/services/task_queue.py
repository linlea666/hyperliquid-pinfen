import logging
from typing import Any, Dict

from rq import Queue
from rq.job import Job
from redis import Redis

from app.core.config import get_settings
from app.services import etl
from app.services import wallets_service
from app.services import tasks_service
from app.services import notifications as notification_service

logger = logging.getLogger(__name__)


def get_queue() -> Queue:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_url)
    return Queue("wallet-sync", connection=redis, default_timeout=600)


def enqueue_wallet_sync(address: str, end_time: int | None = None) -> str:
    """Enqueue wallet sync job; returns job id."""
    q = get_queue()
    job: Job = q.enqueue(run_wallet_sync, address, end_time)
    logger.info("Enqueued wallet sync", extra={"address": address, "job_id": job.id})
    return job.id


def run_wallet_sync(address: str, end_time: int | None = None) -> Dict[str, Any]:
    """Worker entrypoint: full sync then scoring."""
    task_id = tasks_service.log_task_start("wallet_sync", {"address": address, "end_time": end_time})
    try:
        ledger = etl.sync_ledger(address, end_time=end_time)
        fills = etl.sync_fills(address, end_time=end_time)
        positions = etl.sync_positions(address)
        orders = etl.sync_orders(address)
        portfolio_points = etl.sync_portfolio_series(address)
        wallets_service.update_sync_status(address)
        result = {
            "fills": fills,
            "ledger": ledger,
            "positions": positions,
            "orders": orders,
            "portfolio_points": portfolio_points,
        }
        tasks_service.log_task_end(task_id, "completed", result=result)
        return result
    except Exception as exc:
        tasks_service.log_task_end(task_id, "failed", error=str(exc))
        try:
            notification_service.send_notification(
                template_id=1,
                recipient=get_settings().smtp_from,
                payload={"wallet": address, "error": str(exc)},
            )
        except Exception:
            logger.warning("Failed to send failure notification", exc_info=True)
        raise
