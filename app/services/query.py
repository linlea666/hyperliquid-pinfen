from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select

from app.core.database import session_scope
from app.models import FetchCursor, Fill, LedgerEvent, OrderHistory, PositionSnapshot
from app.services import local_cache

# Export model references for routing
LedgerEventModel = LedgerEvent
FillModel = Fill
PositionModel = PositionSnapshot
OrderModel = OrderHistory

CACHE_KIND_MAP = {
    LedgerEventModel: "ledger",
    FillModel: "fills",
    OrderModel: "orders",
    PositionModel: "positions",
}


def get_cursors(user: str) -> Dict[str, int]:
    with session_scope() as session:
        rows = session.execute(select(FetchCursor).where(FetchCursor.user == user)).scalars().all()
        return {r.cursor_type: r.last_time_ms for r in rows}


def latest_records(user: str, limit: int = 20) -> Dict[str, List[dict]]:
    """Return latest ledger, fills, positions, orders as dicts (limited)."""
    limit = min(max(limit, 1), 100)
    with session_scope() as session:
        ledger = (
            session.execute(
                select(LedgerEvent).where(LedgerEvent.user == user).order_by(desc(LedgerEvent.time_ms)).limit(limit)
            )
            .scalars()
            .all()
        )
        fills = (
            session.execute(
                select(Fill).where(Fill.user == user).order_by(desc(Fill.time_ms)).limit(limit)
            )
            .scalars()
            .all()
        )
        positions = (
            session.execute(
                select(PositionSnapshot)
                .where(PositionSnapshot.user == user)
                .order_by(desc(PositionSnapshot.time_ms))
                .limit(limit)
            )
            .scalars()
            .all()
        )
        orders = (
            session.execute(
                select(OrderHistory).where(OrderHistory.user == user).order_by(desc(OrderHistory.time_ms)).limit(limit)
            )
            .scalars()
            .all()
        )

    def model_to_dict(obj):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    def with_cache(records: List, model, kind: str):
        if records:
            return [model_to_dict(o) for o in records]
        cached = local_cache.read_events(user, kind)
        return cached[:limit]

    return {
        "ledger": with_cache(ledger, LedgerEventModel, "ledger"),
        "fills": with_cache(fills, FillModel, "fills"),
        "positions": with_cache(positions, PositionModel, "positions"),
        "orders": with_cache(orders, OrderModel, "orders"),
    }


def _fill_summary_from_rows(rows: List[dict]) -> dict:
    total_pnl = Decimal(0)
    wins = 0
    losses = 0
    breakeven = 0
    for row in rows:
        value = Decimal(str(row.get("closed_pnl") or 0))
        total_pnl += value
        if value > 0:
            wins += 1
        elif value < 0:
            losses += 1
        else:
            breakeven += 1
    return {
        "total_pnl": str(total_pnl),
        "win_trades": wins,
        "loss_trades": losses,
        "break_even_trades": breakeven,
    }


def paged_events(model, user: str, start_time: int = None, end_time: int = None, limit: int = 50, offset: int = 0):
    conditions = [model.user == user]
    if start_time is not None:
        conditions.append(model.time_ms >= start_time)
    if end_time is not None:
        conditions.append(model.time_ms <= end_time)

    summary: Optional[dict] = None

    with session_scope() as session:
        query = select(model).where(and_(*conditions)).order_by(desc(model.time_ms)).offset(offset).limit(limit)
        rows = session.execute(query).scalars().all()
        total = session.execute(
            select(func.count()).select_from(select(model).where(and_(*conditions)).subquery())
        ).scalar_one()

        if model is FillModel:
            total_pnl = session.execute(
                select(func.coalesce(func.sum(Fill.closed_pnl), 0)).where(and_(*conditions))
            ).scalar_one()
            wins = session.execute(
                select(func.count()).select_from(Fill).where(and_(*conditions), Fill.closed_pnl > 0)
            ).scalar_one()
            losses = session.execute(
                select(func.count()).select_from(Fill).where(and_(*conditions), Fill.closed_pnl < 0)
            ).scalar_one()
            breakeven = session.execute(
                select(func.count()).select_from(Fill).where(and_(*conditions), Fill.closed_pnl == 0)
            ).scalar_one()
            summary = {
                "total_pnl": str(total_pnl or 0),
                "win_trades": int(wins or 0),
                "loss_trades": int(losses or 0),
                "break_even_trades": int(breakeven or 0),
            }

    def model_to_dict(obj):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    items = [model_to_dict(o) for o in rows]
    if total == 0:
        cache_kind = CACHE_KIND_MAP.get(model)
        if cache_kind:
            cached = local_cache.read_events(user, cache_kind, start_time=start_time, end_time=end_time)
            total = len(cached)
            items = cached[offset : offset + limit]
            if model is FillModel:
                summary = _fill_summary_from_rows(cached)

    if model is FillModel and summary is None:
        summary = _fill_summary_from_rows(items)
    result = {"items": items, "total": total}
    if summary is not None:
        result["summary"] = summary
    return result
