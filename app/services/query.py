from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from sqlalchemy import and_, desc, func, select

from app.core.database import session_scope
from app.models import FetchCursor, Fill, LedgerEvent, OrderHistory, PositionSnapshot

# Export model references for routing
LedgerEventModel = LedgerEvent
FillModel = Fill
PositionModel = PositionSnapshot
OrderModel = OrderHistory


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

    return {
        "ledger": [model_to_dict(o) for o in ledger],
        "fills": [model_to_dict(o) for o in fills],
        "positions": [model_to_dict(o) for o in positions],
        "orders": [model_to_dict(o) for o in orders],
    }


def paged_events(model, user: str, start_time: int = None, end_time: int = None, limit: int = 50, offset: int = 0):
    conditions = [model.user == user]
    if start_time is not None:
        conditions.append(model.time_ms >= start_time)
    if end_time is not None:
        conditions.append(model.time_ms <= end_time)

    with session_scope() as session:
        query = select(model).where(and_(*conditions)).order_by(desc(model.time_ms)).offset(offset).limit(limit)
        rows = session.execute(query).scalars().all()
        total = session.execute(
            select(func.count()).select_from(select(model).where(and_(*conditions)).subquery())
        ).scalar_one()

    def model_to_dict(obj):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    return {"items": [model_to_dict(o) for o in rows], "total": total}
