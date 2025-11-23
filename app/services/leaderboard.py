import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import Select, desc, select

from app.core.database import session_scope
from app.models import Leaderboard, LeaderboardResult, WalletMetric
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
        return lb


def run_leaderboard(lb_id: int, limit: int = 20) -> List[LeaderboardResult]:
    with session_scope() as session:
        lb = session.get(Leaderboard, lb_id)
        if not lb:
            raise ValueError("Leaderboard not found")
        sort_key = lb.sort_key or "total_pnl"
        sort_column = getattr(WalletMetric, sort_key, WalletMetric.total_pnl)
        order_column = sort_column.desc() if (lb.sort_order or "desc").lower() == "desc" else sort_column.asc()
        previous_top = (
            session.execute(
                select(LeaderboardResult)
                .where(LeaderboardResult.leaderboard_id == lb_id, LeaderboardResult.rank == 1)
            )
            .scalars()
            .first()
        )
        metrics_stmt = select(WalletMetric).order_by(order_column).limit(limit)
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
    lb_ids = [lb.id for lb in list_leaderboards(public_only=False)]
    updated = []
    for lb_id in lb_ids:
        try:
            run_leaderboard(lb_id, limit=limit)
            updated.append(lb_id)
        except Exception as exc:
            logger.warning("Failed to run leaderboard %s", lb_id, exc_info=True)
    return updated
