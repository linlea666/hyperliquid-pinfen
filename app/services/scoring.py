import logging
from decimal import Decimal
from typing import Tuple

from sqlalchemy import asc, select

from app.core.database import session_scope
from app.models import Fill, WalletMetric, WalletScore

logger = logging.getLogger(__name__)


def compute_metrics(user: str) -> Tuple[WalletMetric, WalletScore]:
    """Compute basic metrics and a naive score/level."""
    with session_scope() as session:
        fills = (
            session.execute(select(Fill).where(Fill.user == user).order_by(asc(Fill.time_ms)))
            .scalars()
            .all()
        )
        trades = len(fills)
        if trades == 0:
            import time
            now_ms = int(time.time() * 1000)
            metric = WalletMetric(
                user=user,
                as_of=now_ms,
                trades=0,
                wins=0,
                losses=0,
                win_rate=Decimal(0),
                total_pnl=Decimal(0),
                total_fees=Decimal(0),
                volume=Decimal(0),
                max_drawdown=Decimal(0),
                avg_pnl=Decimal(0),
            )
            session.add(metric)
            score = WalletScore(user=user, as_of=now_ms, score=Decimal(0), level="N/A", metrics_id=None)
            session.add(score)
            return metric, score

        total_pnl = Decimal(0)
        total_fees = Decimal(0)
        volume = Decimal(0)
        wins = 0
        losses = 0
        equity = Decimal(0)
        peak = Decimal(0)
        max_drawdown = Decimal(0)

        for f in fills:
            pnl = Decimal(f.closed_pnl or 0)
            fee = Decimal(f.fee or 0)
            px = Decimal(f.px or 0)
            sz = Decimal(f.sz or 0)
            notional = abs(px * sz)

            total_pnl += pnl
            total_fees += fee
            volume += notional
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1

            equity += pnl
            peak = max(peak, equity)
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        win_rate = Decimal(wins) / Decimal(trades) if trades else Decimal(0)
        avg_pnl = total_pnl / Decimal(trades)
        as_of = fills[-1].time_ms

        metric = WalletMetric(
            user=user,
            as_of=as_of,
            trades=trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_fees=total_fees,
            volume=volume,
            max_drawdown=max_drawdown,
            avg_pnl=avg_pnl,
        )
        session.add(metric)
        session.flush()  # to get id

        # naive scoring: weighted blend
        score_val = (
            float(win_rate) * 40
            + float(total_pnl / (abs(total_pnl) + Decimal(1))) * 30
            + float((volume and (total_pnl / (volume + Decimal(1))))) * 20
            - float(max_drawdown / (abs(total_pnl) + Decimal(1))) * 10
        )
        score_val = max(0.0, min(100.0, score_val))
        level = "S" if score_val >= 90 else "A+" if score_val >= 80 else "A" if score_val >= 70 else "B" if score_val >= 60 else "C"
        score = WalletScore(user=user, as_of=as_of, score=Decimal(str(round(score_val, 2))), level=level, metrics_id=metric.id)
        session.add(score)
        return metric, score
