from decimal import Decimal
from typing import Optional

from sqlalchemy import desc, select

from app.core.database import session_scope
from app.models import AIAnalysis, AIConfig, WalletMetric


def analyze_wallet(address: str, version: str = "v1") -> AIAnalysis:
    with session_scope() as session:
        metric = (
            session.execute(
                select(WalletMetric)
                .where(WalletMetric.user == address)
                .order_by(desc(WalletMetric.as_of))
            )
            .scalars()
            .first()
        )
        if not metric:
            analysis = AIAnalysis(wallet_address=address, version=version, score=0, style="未知", strengths="暂无数据", risks="暂无数据", suggestion="暂无历史表现，建议先观察。", follow_ratio=0)
            session.add(analysis)
            session.flush()
            session.refresh(analysis)
            return analysis

        win_rate = Decimal(metric.win_rate or 0)
        pnl = Decimal(metric.total_pnl or 0)
        drawdown = Decimal(metric.max_drawdown or 0)
        volume = Decimal(metric.volume or 0)

        style = "趋势交易" if win_rate < Decimal("0.55") and pnl > 0 else "稳健型" if drawdown < abs(pnl) * Decimal("0.3") else "高波动"
        strengths = []
        risks = []

        if win_rate > Decimal("0.6"):
            strengths.append("胜率较高，交易执行稳定")
        if pnl > 0:
            strengths.append("累计收益为正")
        if volume > 0:
            strengths.append("交易活跃度高")
        if drawdown > abs(pnl) * Decimal("0.5"):
            risks.append("历史最大回撤较大，需要关注风险控制")
        if win_rate < Decimal("0.4"):
            risks.append("胜率偏低，可能依赖趋势行情")

        score = min(100, max(0, float(win_rate * 50 + (pnl / (abs(pnl) + 1)) * 30 - (drawdown / (abs(pnl) + 1)) * 20)))
        follow_ratio = max(0, min(100, score))
        suggestion = "适合轻仓跟随，建议动态关注风险指标。" if score >= 70 else "建议观望或小额跟单，避免过度暴露。"

        analysis = AIAnalysis(
            wallet_address=address,
            version=version,
            score=score,
            style=style,
            strengths="\n".join(strengths) if strengths else "暂无突出优势",
            risks="\n".join(risks) if risks else "风险水平可控",
            suggestion=suggestion,
            follow_ratio=follow_ratio,
        )
        session.add(analysis)
        session.flush()
        session.refresh(analysis)
        return analysis


def latest_analysis(address: str) -> Optional[AIAnalysis]:
    with session_scope() as session:
        return (
            session.execute(
                select(AIAnalysis)
                .where(AIAnalysis.wallet_address == address)
                .order_by(desc(AIAnalysis.created_at))
            )
            .scalars()
            .first()
        )


def get_ai_config() -> AIConfig:
    with session_scope() as session:
        config = session.execute(select(AIConfig)).scalars().first()
        if not config:
            config = AIConfig()
            session.add(config)
            session.flush()
            session.refresh(config)
        return config


def update_ai_config(**kwargs) -> AIConfig:
    with session_scope() as session:
        config = session.execute(select(AIConfig)).scalars().first()
        if not config:
            config = AIConfig()
            session.add(config)
            session.flush()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        session.add(config)
        session.flush()
        session.refresh(config)
        return config
