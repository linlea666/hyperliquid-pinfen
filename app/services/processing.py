import json
from datetime import datetime, timedelta
from typing import Optional

import math
from sqlalchemy import asc, desc, func, select, or_, case

from app.core.database import session_scope
from app.models import Wallet, WalletProcessingLog, WalletScore, WalletMetric
from app.services import processing_config

STAGE_META = {
    "sync": {
        "status_field": "sync_status",
        "success_value": "synced",
        "time_field": "last_synced_at",
        "due_field": "next_sync_due",
        "cooldown_key": "sync_cooldown_days",
    },
    "score": {
        "status_field": "score_status",
        "success_value": "scored",
        "time_field": "last_score_at",
        "due_field": "next_score_due",
        "cooldown_key": "score_cooldown_days",
    },
    "ai": {
        "status_field": "ai_status",
        "success_value": "completed",
        "time_field": "last_ai_at",
        "due_field": "next_ai_due",
        "cooldown_key": "ai_cooldown_days",
    },
}


def _get_stage_meta(stage: str) -> dict:
    if stage not in STAGE_META:
        raise ValueError(f"Unknown stage: {stage}")
    return STAGE_META[stage]


def _cooldown_days(stage: str) -> int:
    cfg = processing_config.get_processing_config()
    key = STAGE_META[stage].get("cooldown_key")
    if not key:
        return 1
    return max(1, int(cfg.get(key, 1)))


def prepare_stage(
    address: str,
    stage: str,
    payload: Optional[dict] = None,
    scheduled_by: str = "system",
    force: bool = False,
) -> int:
    """Create a pending processing log and mark wallet stage as pending."""
    meta = _get_stage_meta(stage)
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            raise ValueError(f"wallet {address} not found")
        status_field = meta["status_field"]
        if getattr(wallet, status_field) == "running":
            raise ValueError(f"{stage} stage already running for wallet {address}")
        due_field = meta.get("due_field")
        if due_field and not force:
            next_due = getattr(wallet, due_field)
            if next_due and next_due > datetime.utcnow():
                raise ValueError(f"{stage} stage not due until {next_due.isoformat()}")

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
            due_field = meta.get("due_field")
            if due_field:
                setattr(wallet, due_field, now + timedelta(days=_cooldown_days(log.stage)))
            if log.stage == "score":
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
        "next_sync_due": wallet.next_sync_due.isoformat() if wallet.next_sync_due else None,
        "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
        "next_ai_due": wallet.next_ai_due.isoformat() if wallet.next_ai_due else None,
        "last_error": wallet.last_error,
    }


def _scope_description(cfg: dict) -> tuple[str, dict]:
    scope_type = cfg.get("scope_type", "all")
    if scope_type == "today":
        desc_text = "仅今日导入的钱包"
    elif scope_type == "recent":
        desc_text = f"最近 {cfg.get('scope_recent_days', 7)} 天导入的钱包"
    elif scope_type == "tag":
        tag = cfg.get("scope_tag") or "-"
        desc_text = f"包含标签「{tag}」的钱包"
    else:
        desc_text = "全部钱包"
    return desc_text, {
        "type": scope_type,
        "recent_days": cfg.get("scope_recent_days"),
        "tag": cfg.get("scope_tag"),
        "description": desc_text,
    }


def summary(failed_limit: int = 5) -> dict:
    """Aggregate stage counts & recent failures for operations dashboard."""
    cfg = processing_config.get_processing_config()
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
    sync_counts = next((item["counts"] for item in stage_stats if item["stage"] == "sync"), {})
    pending_wallets = (sync_counts.get("pending", 0) or 0) + (sync_counts.get("running", 0) or 0)
    batches = math.ceil(pending_wallets / cfg["batch_size"]) if pending_wallets else 0
    estimate_seconds = batches * cfg["batch_interval_seconds"]
    desc_text, scope_payload = _scope_description(cfg)
    return {
        "stages": stage_stats,
        "pending_rescore": pending_rescore,
        "pending_wallets": pending_wallets,
        "batch_estimate_seconds": estimate_seconds,
        "scope": scope_payload,
        "failed_logs": failed_logs,
    }


def select_wallets_for_scope(
    scope_type: str,
    recent_days: int,
    tag: Optional[str],
    batch_size: int,
    force: bool = False,
) -> list[str]:
    now = datetime.utcnow()

    score_subq = (
        select(WalletScore.score)
        .where(WalletScore.user == Wallet.address)
        .order_by(desc(WalletScore.as_of))
        .limit(1)
        .scalar_subquery()
    )
    pnl_subq = (
        select(WalletMetric.total_pnl)
        .where(WalletMetric.user == Wallet.address)
        .order_by(desc(WalletMetric.as_of))
        .limit(1)
        .scalar_subquery()
    )
    score_priority = case(
        (score_subq >= 90, 3),
        (score_subq >= 75, 2),
        else_=1,
    )
    pnl_priority = case(
        (pnl_subq >= 100000, 3),
        (pnl_subq >= 20000, 2),
        else_=1,
    )
    priority_expr = score_priority + pnl_priority

    with session_scope() as session:
        stmt = (
            select(Wallet.address)
            .where(Wallet.sync_status.notin_(["running", "pending"]))
        )
        if not force:
            stmt = stmt.where(or_(Wallet.next_sync_due.is_(None), Wallet.next_sync_due <= now))
            stmt = stmt.where(or_(Wallet.next_score_due.is_(None), Wallet.next_score_due <= now))
        if scope_type == "today":
            start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            stmt = stmt.where(Wallet.created_at >= start)
        elif scope_type == "recent":
            stmt = stmt.where(Wallet.created_at >= now - timedelta(days=recent_days))
        elif scope_type == "tag":
            tag = (tag or "").strip()
            if not tag:
                return []
            stmt = stmt.where(Wallet.tags.like(f'%"{tag}"%'))
        stmt = stmt.order_by(desc(priority_expr), asc(Wallet.next_score_due), asc(Wallet.created_at)).limit(batch_size)
        rows = session.execute(stmt).all()
        return [row[0] for row in rows]
