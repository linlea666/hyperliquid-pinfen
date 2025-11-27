import json
import logging
from decimal import Decimal
from pathlib import Path
from typing import Tuple

from sqlalchemy import asc, select

from app.core.database import session_scope
from app.models import Fill, WalletMetric, WalletScore, PortfolioSnapshot
from app.core.config import get_settings

SETTINGS = get_settings()


def _funding_stats(user: str) -> Tuple[Decimal, Decimal]:
    path = SETTINGS.cache_dir / user.lower() / "funding.jsonl"
    paid = Decimal(0)
    received = Decimal(0)
    if not path.exists():
        return paid, received
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                delta = item.get("delta", {})
                amount = Decimal(str(delta.get("usdc", "0") or "0"))
                if amount < 0:
                    paid += -amount
                else:
                    received += amount
            except Exception:
                continue
    return paid, received


def _fee_rates(user: str) -> dict:
    path = SETTINGS.cache_dir / user.lower() / "fees.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "userCrossRate": float(data.get("userCrossRate") or 0),
            "userAddRate": float(data.get("userAddRate") or 0),
            "userSpotCrossRate": float(data.get("userSpotCrossRate") or 0),
            "userSpotAddRate": float(data.get("userSpotAddRate") or 0),
        }
    except Exception:
        return {}


def _portfolio_snapshot(session, user: str, period: str) -> Optional[PortfolioSnapshot]:
    return session.execute(
        select(PortfolioSnapshot).where(PortfolioSnapshot.user == user, PortfolioSnapshot.period == period)
    ).scalar_one_or_none()
from app.services import scoring_config

logger = logging.getLogger(__name__)


def _normalize(value: float, indicator: dict) -> float:
    minimum = indicator.get("min", 0)
    maximum = indicator.get("max", 1)
    if maximum == minimum:
        return 0.0
    norm = (value - minimum) / (maximum - minimum)
    if not indicator.get("higher_is_better", True):
        norm = 1 - norm
    norm = max(0.0, min(1.0, norm))
    return norm * 100


def compute_metrics(user: str) -> Tuple[WalletMetric, WalletScore]:
    """Compute metrics and score based on configurable dimensions."""
    config = scoring_config.get_scoring_config()
    with session_scope() as session:
        fills = (
            session.execute(select(Fill).where(Fill.user == user).order_by(asc(Fill.time_ms)))
            .scalars()
            .all()
        )
        trades = len(fills)
        import time
        now_ms = int(time.time() * 1000)

        period_windows = {
            "1d": 86_400_000,
            "7d": 7 * 86_400_000,
            "30d": 30 * 86_400_000,
            "90d": 90 * 86_400_000,
            "1y": 365 * 86_400_000,
            "all": None,
        }
        period_stats = {
            key: {
                "pnl": Decimal(0),
                "volume": Decimal(0),
                "trades": 0,
            }
            for key in period_windows
        }

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
            for key, window in period_windows.items():
                if window is None or (now_ms - (f.time_ms or now_ms)) <= window:
                    stats = period_stats[key]
                    stats["pnl"] += pnl
                    stats["volume"] += notional
                    stats["trades"] += 1

        win_rate = Decimal(wins) / Decimal(trades) if trades else Decimal(0)
        avg_pnl = total_pnl / Decimal(trades) if trades else Decimal(0)
        as_of = fills[-1].time_ms if fills else now_ms

        details = {
            "total_pnl": float(total_pnl),
            "total_fees": float(total_fees),
            "avg_pnl": float(avg_pnl),
            "win_rate": float(win_rate),
            "max_drawdown": float(max_drawdown),
            "volume": float(volume),
            "trades": trades,
        }
        details["equity_stability"] = max(
            0.0, min(1.0, 1 - float(max_drawdown / (abs(total_pnl) + Decimal(1))))
        )
        details["capital_efficiency"] = max(
            0.0, min(1.0, float((abs(total_pnl) + Decimal(1)) / (volume + Decimal(1))))
        )
        period_results = {}
        for key, stats in period_stats.items():
            pnl_value = stats["pnl"]
            vol_value = stats["volume"]
            pnl_float = float(pnl_value)
            if vol_value:
                ratio = float(pnl_value / vol_value) * 100
            else:
                ratio = pnl_float * 100
            period_results[key] = {
                "pnl": pnl_float,
                "return": ratio,
                "trades": stats["trades"],
        }
        details["periods"] = period_results

        funding_paid, funding_received = _funding_stats(user)
        details["funding_paid"] = float(funding_paid)
        details["funding_received"] = float(funding_received)
        denom = abs(total_pnl) + Decimal(1)
        details["funding_cost_ratio"] = float((funding_paid / denom)) if denom else 0.0

        fee_rates = _fee_rates(user)
        details.update({
            "effective_fee_cross": fee_rates.get("userCrossRate"),
            "effective_fee_add": fee_rates.get("userAddRate"),
        })

        portfolio_week = _portfolio_snapshot(session, user, "week")
        portfolio_month = _portfolio_snapshot(session, user, "month")
        portfolio_all = _portfolio_snapshot(session, user, "allTime")
        if portfolio_week:
            details["portfolio_return_7d"] = float(portfolio_week.return_pct or 0)
            details["portfolio_max_drawdown_7d"] = float(portfolio_week.max_drawdown_pct or 0)
        if portfolio_month:
            details["portfolio_return_30d"] = float(portfolio_month.return_pct or 0)
            details["portfolio_max_drawdown_30d"] = float(portfolio_month.max_drawdown_pct or 0)
        if portfolio_all:
            details["portfolio_return_all"] = float(portfolio_all.return_pct or 0)

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
            details=json.dumps(details),
        )
        session.add(metric)
        session.flush()  # to get id

        dimension_scores = {}
        total_weight = sum(dim.get("weight", 0) for dim in config.get("dimensions", [])) or 1
        for dim in config.get("dimensions", []):
            indicators = dim.get("indicators", [])
            indicator_weight_sum = sum(ind.get("weight", 1) for ind in indicators) or 1
            score_acc = 0.0
            for indicator in indicators:
                field = indicator.get("field")
                value = details.get(field, 0.0)
                normalized = _normalize(value, indicator)
                score_acc += normalized * indicator.get("weight", 1)
            dimension_score = score_acc / indicator_weight_sum if indicators else 0.0
            dimension_scores[dim.get("key", dim.get("name"))] = dimension_score

        overall_score = 0.0
        for dim in config.get("dimensions", []):
            key = dim.get("key", dim.get("name"))
            weight = dim.get("weight", 0)
            overall_score += dimension_scores.get(key, 0) * weight
        overall_score = (overall_score / total_weight) if total_weight else 0.0
        overall_score = max(0.0, min(100.0, overall_score))

        level = "N/A"
        for entry in sorted(config.get("levels", []), key=lambda x: x.get("min_score", 0), reverse=True):
            if overall_score >= entry.get("min_score", 0):
                level = entry.get("level", "N/A")
                break

        score = WalletScore(
            user=user,
            as_of=as_of,
            score=Decimal(str(round(overall_score, 2))),
            level=level,
            metrics_id=metric.id,
            dimension_scores=json.dumps(dimension_scores),
        )
        session.add(score)
        return metric, score
