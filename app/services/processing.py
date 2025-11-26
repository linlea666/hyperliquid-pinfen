import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import desc, func, select

from app.core.database import session_scope
from app.models import Wallet, WalletProcessingLog
from app.services import processing_config

STAGE_META = {
    "sync": {"status_field": "sync_status", "success_value": "synced", "time_field": "last_synced_at"},
    "score": {"status_field": "score_status", "success_value": "scored", "time_field": "last_score_at"},
    "ai": {"status_field": "ai_status", "success_value": "completed", "time_field": "last_ai_at"},
}


def _get_stage_meta(stage: str) -> dict:
    if stage not in STAGE_META:
        raise ValueError(f"Unknown stage: {stage}")
    return STAGE_META[stage]


def _rescore_period_days() -> int:
    cfg = processing_config.get_processing_config()
    return max(1, int(cfg.get("rescore_period_days", 7)))


def prepare_stage(address: str, stage: str, payload: Optional[dict] = None, scheduled_by: str = "system") -> int:
    """Create a pending processing log and mark wallet stage as pending."""
    meta = _get_stage_meta(stage)
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            raise ValueError(f"wallet {address} not found")
        status_field = meta["status_field"]
        if getattr(wallet, status_field) == "running":
            raise ValueError(f"{stage} stage already running for wallet {address}")

        attempt = (
            session.execute(
                select(func.max(WalletProcessingLog.attempt)).where(
                    WalletProcessingLog.wallet_address == address,
                    WalletProcessingLog.stage == stage,
                )
            ).scalar()
            or 0
        ) + 1

        log = WalletProcessingLog(
            wallet_address=address,
            stage=stage,
            status="pending",
            payload=json.dumps(payload) if payload else None,
            attempt=attempt,
            scheduled_by=scheduled_by,
        )
        setattr(wallet, status_field, "pending")
        session.add(wallet)
        session.add(log)
        session.flush()
        return log.id


def mark_stage_running(log_id: int) -> Optional[str]:
    with session_scope() as session:
        log = session.get(WalletProcessingLog, log_id)
        if not log:
            return None
        wallet = session.execute(select(Wallet).where(Wallet.address == log.wallet_address)).scalar_one_or_none()
        if wallet:
            meta = _get_stage_meta(log.stage)
            setattr(wallet, meta["status_field"], "running")
            wallet.last_error = None
            session.add(wallet)
        log.status = "running"
        log.started_at = datetime.utcnow()
        session.add(log)
        session.flush()
        return log.wallet_address


def mark_stage_success(log_id: int, result: Optional[dict] = None) -> None:
    now = datetime.utcnow()
    with session_scope() as session:
        log = session.get(WalletProcessingLog, log_id)
        if not log:
            return
        wallet = session.execute(select(Wallet).where(Wallet.address == log.wallet_address)).scalar_one_or_none()
        if wallet:
            meta = _get_stage_meta(log.stage)
            setattr(wallet, meta["status_field"], meta["success_value"])
            time_field = meta.get("time_field")
            if time_field:
                setattr(wallet, time_field, now)
            wallet.last_error = None
            if log.stage == "score":
                wallet.next_score_due = now + timedelta(days=_rescore_period_days())
                wallet.status = "scored"
            elif log.stage == "sync":
                wallet.status = "synced"
            elif log.stage == "ai":
                wallet.status = "analyzed"
            session.add(wallet)

        log.status = "success"
        log.finished_at = now
        if result is not None:
            log.result = json.dumps(result)
        session.add(log)


def mark_stage_failure(log_id: int, error: str) -> None:
    with session_scope() as session:
        log = session.get(WalletProcessingLog, log_id)
        if not log:
            return
        wallet = session.execute(select(Wallet).where(Wallet.address == log.wallet_address)).scalar_one_or_none()
        if wallet:
            meta = _get_stage_meta(log.stage)
            setattr(wallet, meta["status_field"], "failed")
            wallet.last_error = error
            wallet.status = "failed"
            session.add(wallet)

        log.status = "failed"
        log.error = error
        log.finished_at = datetime.utcnow()
        session.add(log)


def list_logs(
    address: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    with session_scope() as session:
        stmt = (
            select(WalletProcessingLog)
            .order_by(desc(WalletProcessingLog.created_at))
            .offset(offset)
            .limit(limit)
        )
        if address:
            stmt = stmt.where(WalletProcessingLog.wallet_address == address)
        if stage:
            stmt = stmt.where(WalletProcessingLog.stage == stage)
        if status:
            stmt = stmt.where(WalletProcessingLog.status == status)
        return session.execute(stmt).scalars().all()


def get_wallet_snapshot(address: str) -> Optional[dict]:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
    if not wallet:
        return None
    return {
        "sync_status": wallet.sync_status,
        "score_status": wallet.score_status,
        "ai_status": wallet.ai_status,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "last_score_at": wallet.last_score_at.isoformat() if wallet.last_score_at else None,
        "last_ai_at": wallet.last_ai_at.isoformat() if wallet.last_ai_at else None,
        "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
        "last_error": wallet.last_error,
    }


def summary(failed_limit: int = 5) -> dict:
    """Aggregate stage counts & recent failures for operations dashboard."""
    with session_scope() as session:
        stage_stats = []
        for stage, meta in STAGE_META.items():
            field = getattr(Wallet, meta["status_field"])
            rows = session.execute(select(field, func.count()).group_by(field)).all()
            counts: dict[str, int] = {}
            for status_value, count in rows:
                key = status_value or "unknown"
                counts[key] = count
            stage_stats.append({"stage": stage, "counts": counts})

        pending_rescore = session.execute(
            select(func.count())
            .select_from(Wallet)
            .where(Wallet.next_score_due.is_not(None), Wallet.next_score_due <= datetime.utcnow())
        ).scalar_one()

        failed_logs = (
            session.execute(
                select(WalletProcessingLog)
                .where(WalletProcessingLog.status == "failed")
                .order_by(desc(WalletProcessingLog.created_at))
                .limit(failed_limit)
            )
            .scalars()
            .all()
        )
    return {
        "stages": stage_stats,
        "pending_rescore": pending_rescore,
        "failed_logs": failed_logs,
    }
