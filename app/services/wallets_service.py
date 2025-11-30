from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, select, case

from app.core.database import session_scope
from app.models import (
    AIAnalysis,
    Fill,
    LedgerEvent,
    Wallet,
    WalletImportRecord,
    WalletMetric,
    WalletScore,
    WalletTag,
    Tag,
    PortfolioSnapshot,
    WalletFollow,
)
from app.services import ai as ai_service

LEDGER_INFLOW_TYPES = {"deposit", "vaultDeposit", "vaultDistribution"}
LEDGER_OUTFLOW_TYPES = {"withdraw", "vaultWithdraw"}


def _serialize_sa(obj):
    if not obj:
        return None
    data = obj.__dict__.copy()
    data.pop("_sa_instance_state", None)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


PERIOD_PRESETS = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
    "180d": timedelta(days=180),
    "365d": timedelta(days=365),
}


def _period_cutoff_ms(period: Optional[str]) -> Optional[int]:
    if not period or period == "all":
        return None
    delta = PERIOD_PRESETS.get(period)
    if not delta:
        return None
    cutoff = datetime.utcnow() - delta
    return int(cutoff.timestamp() * 1000)


def _tags_map(session, addresses: List[str]) -> Dict[str, List[dict]]:
    if not addresses:
        return {}
    stmt = (
        select(WalletTag.wallet_address, Tag)
        .join(Tag, Tag.id == WalletTag.tag_id)
        .where(WalletTag.wallet_address.in_(addresses))
    )
    rows = session.execute(stmt).all()
    mapping: Dict[str, List[dict]] = {}
    for address, tag in rows:
        mapping.setdefault(address, []).append(
            {
                "id": tag.id,
                "name": tag.name,
                "type": tag.type,
                "color": tag.color,
                "icon": tag.icon,
            }
        )
    return mapping


def _portfolio_map(session, addresses: List[str]) -> Dict[str, Dict[str, dict]]:
    if not addresses:
        return {}
    rows = (
        session.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.user.in_(addresses))
        )
        .scalars()
        .all()
    )
    mapping: Dict[str, Dict[str, dict]] = {}
    for snapshot in rows:
        mapping.setdefault(snapshot.user, {})[snapshot.period] = {
            "return_pct": str(snapshot.return_pct) if snapshot.return_pct is not None else None,
            "max_drawdown_pct": str(snapshot.max_drawdown_pct) if snapshot.max_drawdown_pct is not None else None,
            "volume": str(snapshot.volume) if snapshot.volume is not None else None,
            "updated_at": snapshot.updated_at.isoformat(),
        }
    return mapping


def list_wallets(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    period: Optional[str] = None,
    sort_key: Optional[str] = None,
    sort_order: str = "desc",
    followed_only: bool = False,
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    ai_available = ai_service.get_ai_config().is_enabled
    normalized_period = None
    if period and (period == "all" or period in PERIOD_PRESETS):
        normalized_period = period
    conditions = []
    if status:
        conditions.append(Wallet.status == status)
    if search:
        like_pattern = f"%{search.lower()}%"
        conditions.append(func.lower(Wallet.address).like(like_pattern))
    if tag:
        conditions.append(Wallet.tags.like(f'%"{tag}"%'))

    with session_scope() as session:
        count_query = select(func.count()).select_from(Wallet)
        if followed_only:
            count_query = count_query.join(WalletFollow, Wallet.address == WalletFollow.wallet_address)
        period_cutoff = _period_cutoff_ms(normalized_period)
        metric_latest = (
            select(
                WalletMetric.user.label("user"),
                func.max(WalletMetric.as_of).label("max_as_of"),
            )
        )
        if period_cutoff:
            metric_latest = metric_latest.where(WalletMetric.as_of >= period_cutoff)
        metric_latest = metric_latest.group_by(WalletMetric.user).subquery()

        metric_view = (
            select(
                WalletMetric.user.label("metric_user"),
                WalletMetric.win_rate.label("metric_win_rate"),
                WalletMetric.total_pnl.label("metric_total_pnl"),
                WalletMetric.avg_pnl.label("metric_avg_pnl"),
                WalletMetric.volume.label("metric_volume"),
                WalletMetric.trades.label("metric_trades"),
                WalletMetric.max_drawdown.label("metric_max_drawdown"),
                WalletMetric.wins.label("metric_wins"),
                WalletMetric.losses.label("metric_losses"),
                WalletMetric.as_of.label("metric_as_of"),
                WalletMetric.created_at.label("metric_created_at"),
                WalletMetric.details.label("metric_details"),
            )
            .join(
                metric_latest,
                (WalletMetric.user == metric_latest.c.user) & (WalletMetric.as_of == metric_latest.c.max_as_of),
            )
            .subquery()
        )

        portfolio_week = (
            select(
                PortfolioSnapshot.user.label("portfolio_week_user"),
                PortfolioSnapshot.return_pct.label("portfolio_week_return"),
                PortfolioSnapshot.max_drawdown_pct.label("portfolio_week_drawdown"),
            )
            .where(PortfolioSnapshot.period == "week")
            .subquery()
        )
        portfolio_month = (
            select(
                PortfolioSnapshot.user.label("portfolio_month_user"),
                PortfolioSnapshot.return_pct.label("portfolio_month_return"),
                PortfolioSnapshot.max_drawdown_pct.label("portfolio_month_drawdown"),
            )
            .where(PortfolioSnapshot.period == "month")
            .subquery()
        )

        ai_latest = (
            select(
                AIAnalysis.wallet_address.label("ai_user"),
                func.max(AIAnalysis.created_at).label("max_created"),
            )
            .group_by(AIAnalysis.wallet_address)
            .subquery()
        )

        ai_view = (
            select(
                AIAnalysis.wallet_address.label("ai_view_user"),
                AIAnalysis.score.label("ai_score"),
                AIAnalysis.follow_ratio.label("ai_follow_ratio"),
                AIAnalysis.style.label("ai_style"),
                AIAnalysis.created_at.label("ai_created_at"),
            )
            .join(
                ai_latest,
                (AIAnalysis.wallet_address == ai_latest.c.ai_user)
                & (AIAnalysis.created_at == ai_latest.c.max_created),
            )
            .subquery()
        )

        sort_key_map = {
            "win_rate": metric_view.c.metric_win_rate,
            "total_pnl": metric_view.c.metric_total_pnl,
            "avg_pnl": metric_view.c.metric_avg_pnl,
            "volume": metric_view.c.metric_volume,
            "trades": metric_view.c.metric_trades,
            "max_drawdown": metric_view.c.metric_max_drawdown,
            "portfolio_week_return": portfolio_week.c.portfolio_week_return,
            "portfolio_week_drawdown": portfolio_week.c.portfolio_week_drawdown,
            "portfolio_month_return": portfolio_month.c.portfolio_month_return,
            "portfolio_month_drawdown": portfolio_month.c.portfolio_month_drawdown,
            "ai_score": ai_view.c.ai_score,
            "ai_follow_ratio": ai_view.c.ai_follow_ratio,
        }

        metric_columns = [
            metric_view.c.metric_user,
            metric_view.c.metric_win_rate,
            metric_view.c.metric_total_pnl,
            metric_view.c.metric_avg_pnl,
            metric_view.c.metric_volume,
            metric_view.c.metric_trades,
            metric_view.c.metric_max_drawdown,
            metric_view.c.metric_wins,
            metric_view.c.metric_losses,
            metric_view.c.metric_as_of,
            metric_view.c.metric_created_at,
            metric_view.c.metric_details,
        ]

        portfolio_columns = [
            portfolio_week.c.portfolio_week_return,
            portfolio_week.c.portfolio_week_drawdown,
            portfolio_month.c.portfolio_month_return,
            portfolio_month.c.portfolio_month_drawdown,
        ]

        ai_columns = [
            ai_view.c.ai_view_user,
            ai_view.c.ai_score,
            ai_view.c.ai_follow_ratio,
            ai_view.c.ai_style,
            ai_view.c.ai_created_at,
        ]

        data_query = (
            select(
                Wallet,
                *metric_columns,
                *portfolio_columns,
                *ai_columns,
                WalletFollow.wallet_address.label("follow_wallet"),
                WalletFollow.note.label("follow_note"),
            )
            .outerjoin(metric_view, Wallet.address == metric_view.c.metric_user)
            .outerjoin(portfolio_week, Wallet.address == portfolio_week.c.portfolio_week_user)
            .outerjoin(portfolio_month, Wallet.address == portfolio_month.c.portfolio_month_user)
            .outerjoin(ai_view, Wallet.address == ai_view.c.ai_view_user)
            .offset(offset)
            .limit(limit)
        )
        if conditions:
            predicate = and_(*conditions)
            count_query = count_query.where(predicate)
            data_query = data_query.where(predicate)

        if followed_only:
            count_query = count_query.join(WalletFollow, Wallet.address == WalletFollow.wallet_address)
            data_query = data_query.join(WalletFollow, Wallet.address == WalletFollow.wallet_address)
        else:
            data_query = data_query.outerjoin(WalletFollow, Wallet.address == WalletFollow.wallet_address)

        sort_column = sort_key_map.get(sort_key or "")
        if sort_column is not None:
            order_fn = desc if sort_order.lower() == "desc" else asc
            nulls_last_expr = case((sort_column.is_(None), 1), else_=0)
            data_query = data_query.order_by(nulls_last_expr, order_fn(sort_column), desc(Wallet.created_at))
        else:
            data_query = data_query.order_by(desc(Wallet.created_at))

        total = session.execute(count_query).scalar_one()
        rows = session.execute(data_query).all()
        addresses = [row[0].address for row in rows]
        tags_map = _tags_map(session, addresses)
        portfolio_map = _portfolio_map(session, addresses)

    def serialize(row) -> dict:
        wallet: Wallet = row[0]
        raw_tags = tags_map.get(wallet.address) or (json.loads(wallet.tags) if wallet.tags else [])
        tags = []
        for tag in raw_tags:
            if isinstance(tag, dict):
                tags.append(tag)
            else:
                tags.append({"name": tag})
        metric_row = row._mapping
        metric_user = metric_row.get("metric_user")
        metric_dict = None
        if metric_user:
            metric_dict = {
                "win_rate": str(metric_row["metric_win_rate"]) if metric_row.get("metric_win_rate") is not None else None,
                "total_pnl": str(metric_row["metric_total_pnl"]) if metric_row.get("metric_total_pnl") is not None else None,
                "avg_pnl": str(metric_row["metric_avg_pnl"]) if metric_row.get("metric_avg_pnl") is not None else None,
                "volume": str(metric_row["metric_volume"]) if metric_row.get("metric_volume") is not None else None,
                "trades": int(metric_row["metric_trades"]) if metric_row.get("metric_trades") is not None else None,
                "max_drawdown": str(metric_row["metric_max_drawdown"])
                if metric_row.get("metric_max_drawdown") is not None
                else None,
                "wins": int(metric_row["metric_wins"]) if metric_row.get("metric_wins") is not None else None,
                "losses": int(metric_row["metric_losses"]) if metric_row.get("metric_losses") is not None else None,
                "as_of": int(metric_row["metric_as_of"]) if metric_row.get("metric_as_of") is not None else None,
                "updated_at": metric_row["metric_created_at"].isoformat()
                if metric_row.get("metric_created_at") is not None
                else None,
            }
            details = metric_row.get("metric_details")
            if details:
                try:
                    metric_dict["details"] = json.loads(details)
                except Exception:
                    metric_dict["details"] = None
        active_days = None
        if wallet.first_trade_time:
            active_days = max(1, (datetime.utcnow() - wallet.first_trade_time).days)
        result = {
            "address": wallet.address,
            "status": wallet.status,
            "sync_status": wallet.sync_status,
            "score_status": wallet.score_status,
            "ai_status": wallet.ai_status,
            "tags": tags,
            "source": wallet.source,
            "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
            "last_score_at": wallet.last_score_at.isoformat() if wallet.last_score_at else None,
            "last_ai_at": wallet.last_ai_at.isoformat() if wallet.last_ai_at else None,
            "next_sync_due": wallet.next_sync_due.isoformat() if wallet.next_sync_due else None,
            "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
            "next_ai_due": wallet.next_ai_due.isoformat() if wallet.next_ai_due else None,
            "last_error": wallet.last_error,
            "note": wallet.note,
            "created_at": wallet.created_at.isoformat(),
            "first_trade_time": wallet.first_trade_time.isoformat() if wallet.first_trade_time else None,
            "active_days": active_days,
            "metric": metric_dict,
            "metric_period": normalized_period if metric_dict else None,
            "is_followed": bool(metric_row.get("follow_wallet")),
            "follow_note": metric_row.get("follow_note"),
            "ai_enabled": ai_available,
        }
        portfolio_stats = portfolio_map.get(wallet.address)
        if portfolio_stats:
            result["portfolio"] = portfolio_stats
        ai_user = metric_row.get("ai_view_user")
        if ai_user:
            result["ai_analysis"] = {
                "score": float(metric_row.get("ai_score")) if metric_row.get("ai_score") is not None else None,
                "follow_ratio": float(metric_row.get("ai_follow_ratio")) if metric_row.get("ai_follow_ratio") is not None else None,
                "style": metric_row.get("ai_style"),
                "updated_at": metric_row.get("ai_created_at").isoformat() if metric_row.get("ai_created_at") else None,
            }
        return result

    return {"total": total, "items": [serialize(row) for row in rows]}


def get_wallet_detail(address: str) -> Optional[dict]:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            return None
        metric_query = (
            select(WalletMetric)
            .where(WalletMetric.user == address)
            .order_by(desc(WalletMetric.as_of))
            .limit(1)
        )
        metric = session.execute(metric_query).scalars().first()
        score = (
            session.execute(
                select(WalletScore)
                .where(WalletScore.user == address)
                .order_by(desc(WalletScore.as_of))
            )
            .scalars()
            .first()
        )
        ai_analysis = (
            session.execute(
                select(AIAnalysis)
                .where(AIAnalysis.wallet_address == address)
                .order_by(desc(AIAnalysis.created_at))
                .limit(1)
            )
            .scalars()
            .first()
        )
        tags_map = _tags_map(session, [address])
        portfolio_stats = _portfolio_map(session, [address]).get(address)
        ledger_summary = _ledger_summary(session, address)
        follow_entry = (
            session.execute(select(WalletFollow).where(WalletFollow.wallet_address == address)).scalars().first()
        )
    raw_tags = tags_map.get(address) or (json.loads(wallet.tags) if wallet.tags else [])
    normalized_tags = []
    for tag in raw_tags:
        if isinstance(tag, dict):
            normalized_tags.append(tag)
        else:
            normalized_tags.append({"name": tag})
    data = {
        "address": wallet.address,
        "status": wallet.status,
        "sync_status": wallet.sync_status,
        "score_status": wallet.score_status,
        "ai_status": wallet.ai_status,
        "tags": normalized_tags,
        "source": wallet.source,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "last_score_at": wallet.last_score_at.isoformat() if wallet.last_score_at else None,
        "last_ai_at": wallet.last_ai_at.isoformat() if wallet.last_ai_at else None,
        "next_sync_due": wallet.next_sync_due.isoformat() if wallet.next_sync_due else None,
        "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
        "next_ai_due": wallet.next_ai_due.isoformat() if wallet.next_ai_due else None,
        "last_error": wallet.last_error,
        "note": wallet.note,
        "created_at": wallet.created_at.isoformat(),
        "first_trade_time": wallet.first_trade_time.isoformat() if wallet.first_trade_time else None,
        "active_days": max(1, (datetime.utcnow() - wallet.first_trade_time).days)
        if wallet.first_trade_time
        else None,
    }
    metric_dict = _serialize_sa(metric)
    if metric_dict and metric.details:
        try:
            metric_dict["details"] = json.loads(metric.details)
        except Exception:
            pass
    score_dict = _serialize_sa(score)
    if score_dict and score.dimension_scores:
        try:
            score_dict["dimension_scores"] = json.loads(score.dimension_scores)
        except Exception:
            pass
    if metric_dict:
        data["metric"] = metric_dict
    if score_dict:
        data["score"] = score_dict
    if portfolio_stats:
        data["portfolio"] = portfolio_stats
    ai_dict = _serialize_sa(ai_analysis)
    if ai_dict:
        data["ai_analysis"] = ai_dict
    if ledger_summary:
        data["ledger_summary"] = ledger_summary
    data["is_followed"] = bool(follow_entry)
    data["follow_note"] = follow_entry.note if follow_entry else None
    data["ai_enabled"] = ai_service.get_ai_config().is_enabled
    return data


def _ledger_summary(session, address: str) -> Optional[dict]:
    value_expr = func.coalesce(LedgerEvent.usdc_value, LedgerEvent.amount, 0)
    inflow_case = case((LedgerEvent.delta_type.in_(tuple(LEDGER_INFLOW_TYPES)), value_expr), else_=0)
    outflow_case = case((LedgerEvent.delta_type.in_(tuple(LEDGER_OUTFLOW_TYPES)), value_expr), else_=0)
    inflow_count_case = case((LedgerEvent.delta_type.in_(tuple(LEDGER_INFLOW_TYPES)), 1), else_=0)
    outflow_count_case = case((LedgerEvent.delta_type.in_(tuple(LEDGER_OUTFLOW_TYPES)), 1), else_=0)
    row = session.execute(
        select(
            func.sum(inflow_case).label("inflow_total"),
            func.sum(outflow_case).label("outflow_total"),
            func.sum(inflow_count_case).label("inflow_count"),
            func.sum(outflow_count_case).label("outflow_count"),
        ).where(LedgerEvent.user == address)
    ).first()
    if not row:
        return None
    inflow_total = row.inflow_total or Decimal(0)
    outflow_total = row.outflow_total or Decimal(0)
    summary = {
        "inflow_total": str(inflow_total),
        "outflow_total": str(outflow_total),
        "net_inflow": str(inflow_total - outflow_total),
        "inflow_count": int(row.inflow_count or 0),
        "outflow_count": int(row.outflow_count or 0),
    }
    return summary


def get_wallet_overview() -> dict:
    with session_scope() as session:
        total_wallets = session.execute(select(func.count()).select_from(Wallet)).scalar_one()
        pending_wallets = session.execute(select(func.count()).select_from(Wallet).where(Wallet.sync_status == "pending")).scalar_one()
        running_wallets = session.execute(select(func.count()).select_from(Wallet).where(Wallet.sync_status == "running")).scalar_one()
        failed_wallets = session.execute(select(func.count()).select_from(Wallet).where(Wallet.sync_status == "failed")).scalar_one()
        synced_wallets = (
            session.execute(select(func.count()).select_from(Wallet).where(Wallet.sync_status == "synced")).scalar_one()
            if total_wallets
            else 0
        )
        ledger_events = session.execute(select(func.count()).select_from(LedgerEvent)).scalar_one()
        fills = session.execute(select(func.count()).select_from(Fill)).scalar_one()
        last_sync = (
            session.execute(select(func.max(Wallet.last_synced_at)).select_from(Wallet)).scalar_one()
        )
        follow_total = session.execute(select(func.count()).select_from(WalletFollow)).scalar_one()
        follow_today = session.execute(
            select(func.count())
            .select_from(WalletFollow)
            .where(WalletFollow.created_at >= datetime.utcnow() - timedelta(days=1))
        ).scalar_one()
    return {
        "total_wallets": total_wallets,
        "synced_wallets": synced_wallets,
        "pending_wallets": pending_wallets,
        "running_wallets": running_wallets,
        "failed_wallets": failed_wallets,
        "ledger_events": ledger_events,
        "fills": fills,
        "last_sync": last_sync.isoformat() if last_sync else None,
        "followed_wallets": follow_total,
        "followed_today": follow_today,
    }


def set_wallet_follow(address: str, follow: bool, note: Optional[str] = None) -> Optional[dict]:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            return None
        existing = (
            session.execute(select(WalletFollow).where(WalletFollow.wallet_address == address))
            .scalars()
            .first()
        )
        if follow:
            if existing:
                existing.note = note
                session.add(existing)
            else:
                session.add(WalletFollow(wallet_address=address, note=note))
        else:
            if existing:
                session.delete(existing)
        session.flush()
        latest = (
            session.execute(select(WalletFollow).where(WalletFollow.wallet_address == address))
            .scalars()
            .first()
        )
        return {"address": address, "is_followed": bool(latest), "note": latest.note if latest else None}


def list_followed_wallets(limit: int = 20, offset: int = 0):
    return list_wallets(limit=limit, offset=offset, followed_only=True)


def list_import_records(limit: int = 20, offset: int = 0):
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    with session_scope() as session:
        total = session.execute(select(func.count()).select_from(WalletImportRecord)).scalar_one()
        rows = (
            session.execute(
                select(WalletImportRecord)
                .order_by(desc(WalletImportRecord.created_at))
                .offset(offset)
                .limit(limit)
            )
            .scalars()
            .all()
        )

    items = []
    for row in rows:
        tags = [tag.strip() for tag in (row.tag_list or "").split(",") if tag.strip()]
        items.append(
            {
                "id": row.id,
                "source": row.source,
                "tags": tags,
                "created_by": row.created_by,
                "created_at": row.created_at.isoformat(),
            }
        )
    return {"total": total, "items": items}


def update_wallet_note(address: str, note: Optional[str]) -> Optional[str]:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            return None
        wallet.note = note.strip() if note else None
        session.add(wallet)
        return wallet.note
