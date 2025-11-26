from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, select, case

from app.core.database import session_scope
from app.models import (
    Fill,
    LedgerEvent,
    Wallet,
    WalletImportRecord,
    WalletMetric,
    WalletScore,
    WalletTag,
    Tag,
)


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


def list_wallets(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    period: Optional[str] = None,
    sort_key: Optional[str] = None,
    sort_order: str = "desc",
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
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

        sort_key_map = {
            "win_rate": metric_view.c.metric_win_rate,
            "total_pnl": metric_view.c.metric_total_pnl,
            "avg_pnl": metric_view.c.metric_avg_pnl,
            "volume": metric_view.c.metric_volume,
            "trades": metric_view.c.metric_trades,
            "max_drawdown": metric_view.c.metric_max_drawdown,
        }

        data_query = (
            select(Wallet, metric_view)
            .outerjoin(metric_view, Wallet.address == metric_view.c.metric_user)
            .offset(offset)
            .limit(limit)
        )
        if conditions:
            predicate = and_(*conditions)
            count_query = count_query.where(predicate)
            data_query = data_query.where(predicate)

        sort_column = sort_key_map.get(sort_key or "")
        if sort_column is not None:
            order_fn = desc if sort_order.lower() == "desc" else asc
            nulls_last_expr = case((sort_column.is_(None), 1), else_=0)
            data_query = data_query.order_by(nulls_last_expr, order_fn(sort_column), desc(Wallet.created_at))
        else:
            data_query = data_query.order_by(desc(Wallet.created_at))

        total = session.execute(count_query).scalar_one()
        rows = session.execute(data_query).all()
        wallets: List[Wallet] = []
        metric_rows: Dict[str, Any] = {}
        for row in rows:
            wallet_obj = row[0]
            metric_obj = row[1] if len(row) > 1 else None
            wallets.append(wallet_obj)
            metric_rows[wallet_obj.address] = metric_obj
        addresses = [wallet.address for wallet in wallets]
        tags_map = _tags_map(session, addresses)

    def serialize(wallet: Wallet) -> dict:
        raw_tags = tags_map.get(wallet.address) or (json.loads(wallet.tags) if wallet.tags else [])
        tags = []
        for tag in raw_tags:
            if isinstance(tag, dict):
                tags.append(tag)
            else:
                tags.append({"name": tag})
        metric_row = metric_rows.get(wallet.address)
        metric_dict = None
        if metric_row and metric_row.metric_user:
            metric_dict = {
                "win_rate": str(metric_row.metric_win_rate) if metric_row.metric_win_rate is not None else None,
                "total_pnl": str(metric_row.metric_total_pnl) if metric_row.metric_total_pnl is not None else None,
                "avg_pnl": str(metric_row.metric_avg_pnl) if metric_row.metric_avg_pnl is not None else None,
                "volume": str(metric_row.metric_volume) if metric_row.metric_volume is not None else None,
                "trades": int(metric_row.metric_trades) if metric_row.metric_trades is not None else None,
                "max_drawdown": str(metric_row.metric_max_drawdown)
                if metric_row.metric_max_drawdown is not None
                else None,
                "wins": int(metric_row.metric_wins) if metric_row.metric_wins is not None else None,
                "losses": int(metric_row.metric_losses) if metric_row.metric_losses is not None else None,
                "as_of": int(metric_row.metric_as_of) if metric_row.metric_as_of is not None else None,
                "updated_at": metric_row.metric_created_at.isoformat()
                if metric_row.metric_created_at is not None
                else None,
            }
            if getattr(metric_row, "metric_details", None):
                try:
                    metric_dict["details"] = json.loads(metric_row.metric_details)
                except Exception:
                    metric_dict["details"] = None
        return {
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
            "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
            "last_error": wallet.last_error,
            "created_at": wallet.created_at.isoformat(),
            "metric": metric_dict,
            "metric_period": normalized_period if metric_dict else None,
        }

    return {"total": total, "items": [serialize(row) for row in wallets]}


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
        tags_map = _tags_map(session, [address])
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
        "next_score_due": wallet.next_score_due.isoformat() if wallet.next_score_due else None,
        "last_error": wallet.last_error,
        "created_at": wallet.created_at.isoformat(),
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
    return data


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
    return {
        "total_wallets": total_wallets,
        "synced_wallets": synced_wallets,
        "pending_wallets": pending_wallets,
        "running_wallets": running_wallets,
        "failed_wallets": failed_wallets,
        "ledger_events": ledger_events,
        "fills": fills,
        "last_sync": last_sync.isoformat() if last_sync else None,
    }


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
