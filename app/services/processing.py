import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, select

from app.core.database import session_scope
from app.models import Wallet, WalletProcessingLog
from app.services import admin as admin_service

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
    value = admin_service.get_config("processing.rescore_period_days")
    try:
        days = int(value) if value is not None else 7
    except ValueError:
        days = 7
    return max(1, days)


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
