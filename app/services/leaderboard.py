import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.orm import aliased

from app.core.database import session_scope
from app.models import Leaderboard, LeaderboardResult, WalletMetric, PortfolioSnapshot
from app.services import notifications as notification_service
from app.services import admin as admin_service

logger = logging.getLogger(__name__)


def list_leaderboards(public_only: bool = True) -> List[Leaderboard]:
    with session_scope() as session:
        stmt: Select[Leaderboard] = select(Leaderboard)
        if public_only:
            stmt = stmt.where(Leaderboard.is_public == 1)
        stmt = stmt.order_by(Leaderboard.created_at)
        return session.execute(stmt).scalars().all()


def create_leaderboard(**kwargs) -> Leaderboard:
    with session_scope() as session:
        lb = Leaderboard(**kwargs)
        session.add(lb)
        session.flush()
        session.refresh(lb)
    _refresh_leaderboard_jobs()
    return lb


def update_leaderboard(lb_id: int, **kwargs) -> Leaderboard:
    with session_scope() as session:
        lb = session.get(Leaderboard, lb_id)
        if not lb:
            raise ValueError("Leaderboard not found")
        for key, value in kwargs.items():
            if value is not None:
                setattr(lb, key, value)
        session.add(lb)
        session.flush()
        session.refresh(lb)
    _refresh_leaderboard_jobs()
    return lb


def _refresh_leaderboard_jobs() -> None:
    try:
        from app.services import scheduler

        scheduler.refresh_jobs()
    except Exception:
        logger.debug("Unable to refresh scheduler jobs for leaderboard changes", exc_info=True)


def _extract_periods(metric: WalletMetric) -> dict:
    if not metric.details:
        return {}
    try:
        details = json.loads(metric.details)
        periods = details.get("periods", {})
    except Exception:
        return {}
    keep_keys = ["1d", "7d", "30d", "90d", "1y", "all"]
    payload = {}
    for key in keep_keys:
        if key in periods:
            value = periods[key]
            payload[key] = {
                "pnl": str(value.get("pnl")) if value.get("pnl") is not None else None,
                "return": value.get("return"),
                "trades": value.get("trades"),
            }
    return payload


def run_leaderboard(lb_id: int, limit: int = 20) -> List[LeaderboardResult]:
    with session_scope() as session:
        lb = session.get(Leaderboard, lb_id)
        if not lb:
            raise ValueError("Leaderboard not found")
        effective_limit = lb.result_limit or limit or 20
        sort_key = lb.sort_key or "total_pnl"
        previous_top = (
            session.execute(
                select(LeaderboardResult)
                .where(LeaderboardResult.leaderboard_id == lb_id, LeaderboardResult.rank == 1)
            )
            .scalars()
            .first()
        )
        metrics_stmt = select(WalletMetric)

        portfolio_aliases: dict[str, any] = {}
        joins: list[tuple[Any, Any]] = []

        def ensure_portfolio_alias(period: str):
            if period in portfolio_aliases:
                return portfolio_aliases[period]
            alias = aliased(PortfolioSnapshot, name=f"lb_portfolio_{period}")
            joins.append((alias, and_(alias.user == WalletMetric.user, alias.period == period)))
            portfolio_aliases[period] = alias
            return alias

        def resolve_column(source: str, field: str, period: Optional[str] = None):
            if source == "metric":
                return getattr(WalletMetric, field, None)
            if source == "portfolio":
                alias = ensure_portfolio_alias(period or "month")
                mapping = {
                    "return_pct": alias.return_pct,
                    "max_drawdown_pct": alias.max_drawdown_pct,
                    "volume": alias.volume,
                }
                return mapping.get(field)
            return None

        def parse_sort_column(key: str):
            if key.startswith("portfolio_"):
                parts = key.split("_")
                if len(parts) >= 3:
                    period = parts[1]
                    metric_name = parts[2]
                    field_map = {
                        "return": "return_pct",
                        "drawdown": "max_drawdown_pct",
                    }
                    column = resolve_column("portfolio", field_map.get(metric_name, metric_name), period)
                    if column is not None:
                        return column
            return getattr(WalletMetric, key, None)

        sort_column = parse_sort_column(sort_key) or WalletMetric.total_pnl
        order_column = sort_column.desc() if (lb.sort_order or "desc").lower() == "desc" else sort_column.asc()

        filter_defs = []
        if lb.filters:
            try:
                filter_defs = json.loads(lb.filters)
            except Exception:
                filter_defs = []

        filter_exprs = []
        op_map = {
            ">=" : lambda col, val: col >= val,
            ">" : lambda col, val: col > val,
            "<=" : lambda col, val: col <= val,
            "<" : lambda col, val: col < val,
            "==" : lambda col, val: col == val,
        }
        for filt in filter_defs:
            source = filt.get("source", "metric")
            field = filt.get("field")
            if not field:
                continue
            period = filt.get("period")
            column = resolve_column(source, field, period)
            if column is None:
                continue
            op = filt.get("op", ">=")
            comparator = op_map.get(op)
            if not comparator:
                continue
            value = filt.get("value")
            if value is None:
                continue
            try:
                value_decimal = Decimal(str(value))
            except Exception:
                value_decimal = value
            filter_exprs.append(comparator(column, value_decimal))

        for alias, condition in joins:
            metrics_stmt = metrics_stmt.outerjoin(alias, condition)
        if filter_exprs:
            metrics_stmt = metrics_stmt.where(and_(*filter_exprs))
        metrics_stmt = metrics_stmt.order_by(order_column).limit(effective_limit)
        metrics = session.execute(metrics_stmt).scalars().all()
        session.query(LeaderboardResult).filter(LeaderboardResult.leaderboard_id == lb_id).delete()
        results = []
        for idx, metric in enumerate(metrics, start=1):
            result = LeaderboardResult(
                leaderboard_id=lb_id,
                wallet_address=metric.user,
                rank=idx,
                score=getattr(metric, sort_key, Decimal(0)),
                snapshot_time=datetime.utcnow(),
                metrics=json.dumps(
                    {
                        "trades": metric.trades,
                        "wins": metric.wins,
                        "losses": metric.losses,
                        "win_rate": str(metric.win_rate) if metric.win_rate is not None else None,
                        "total_pnl": str(metric.total_pnl) if metric.total_pnl is not None else None,
                        "avg_pnl": str(metric.avg_pnl) if metric.avg_pnl is not None else None,
                        "periods": _extract_periods(metric),
                    }
                ),
            )
            session.add(result)
            results.append(result)
        session.flush()
        session.refresh(lb)
        # Notify if top wallet changes
        new_top = results[0] if results else None
        if new_top and (not previous_top or previous_top.wallet_address != new_top.wallet_address):
            template_key = admin_service.get_config("leaderboard_notify_template")
            recipient = admin_service.get_config("leaderboard_notify_recipient")
            try:
                template_id = int(template_key) if template_key else None
            except (TypeError, ValueError):
                template_id = None
            if template_id and recipient:
                try:
                    notification_service.send_notification(
                        template_id=template_id,
                        recipient=recipient,
                        payload={
                            "leaderboard": lb.name,
                            "wallet": new_top.wallet_address,
                            "score": str(new_top.score),
                        },
                    )
                except Exception:
                    logger.warning("Failed to send leaderboard notification", exc_info=True)
        return results


def leaderboard_results(lb_id: int) -> List[LeaderboardResult]:
    with session_scope() as session:
        stmt = select(LeaderboardResult).where(LeaderboardResult.leaderboard_id == lb_id).order_by(LeaderboardResult.rank)
        return session.execute(stmt).scalars().all()


def run_all_leaderboards(limit: int = 20) -> List[int]:
    lbs = list_leaderboards(public_only=False)
    updated = []
    for lb in lbs:
        try:
            run_leaderboard(lb.id, limit=lb.result_limit or limit)
            updated.append(lb.id)
        except Exception as exc:
            logger.warning("Failed to run leaderboard %s", lb.id, exc_info=True)
    return updated
