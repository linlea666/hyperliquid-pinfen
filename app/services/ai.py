import json
from decimal import Decimal
from typing import Optional

from sqlalchemy import desc, select

from app.core.database import session_scope, write_lock
from app.models import AIAnalysis, AIConfig, WalletMetric
from app.services import tags as tag_service
from app.services import tasks_service


def analyze_wallet(address: str, version: str = "v1") -> AIAnalysis:
    config = get_ai_config()
    log_id = tasks_service.log_ai_start(wallet_address=address, provider=config.provider, model=config.model or "deepseek-chat")
    try:
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
            analysis = AIAnalysis(
                wallet_address=address,
                version=version,
                score=0,
                style="未知",
                strengths="暂无数据",
                risks="暂无数据",
                suggestion="暂无历史表现，建议先观察。",
                follow_ratio=0,
            )
            with write_lock:
                with session_scope() as write_session:
                    write_session.add(analysis)
                    write_session.flush()
                    write_session.refresh(analysis)
            tasks_service.log_ai_end(
                log_id,
                "success",
                response=f"score={analysis.score}, follow_ratio={analysis.follow_ratio}",
            )
            return analysis

        details = {}
        if metric.details:
            try:
                details = json.loads(metric.details)
            except Exception:
                details = {}
        periods = details.get("periods") or {}
        stats_7d = periods.get("7d") or {}
        stats_30d = periods.get("30d") or {}
        win_rate = Decimal(metric.win_rate or 0)
        pnl = Decimal(metric.total_pnl or 0)
        drawdown = Decimal(metric.max_drawdown or 0)
        volume = Decimal(metric.volume or 0)
        avg_pnl = Decimal(metric.avg_pnl or 0)

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

        def normalize_pct(value, multiply=True):
            if value is None:
                return None
            try:
                num = float(value)
            except Exception:
                return None
            return num * 100 if multiply else num

        month_return_pct = details.get("portfolio_return_30d")
        month_drawdown_pct = details.get("portfolio_max_drawdown_30d")
        week_return_pct = details.get("portfolio_return_7d")
        all_return_pct = details.get("portfolio_return_all")
        funding_cost_ratio = details.get("funding_cost_ratio")

        metrics_payload = {
            "win_rate_pct": float(win_rate * 100),
            "total_pnl": float(pnl),
            "avg_pnl": float(avg_pnl),
            "max_drawdown": float(drawdown),
            "trades_total": int(metric.trades or 0),
            "volume": float(volume),
            "trades_30d": int(stats_30d.get("trades") or 0),
            "trades_7d": int(stats_7d.get("trades") or 0),
            "pnl_30d": float(stats_30d.get("pnl") or 0),
            "pnl_7d": float(stats_7d.get("pnl") or 0),
            "month_return_pct": normalize_pct(month_return_pct),
            "month_drawdown_pct": normalize_pct(month_drawdown_pct),
            "week_return_pct": normalize_pct(week_return_pct),
            "all_return_pct": normalize_pct(all_return_pct),
            "funding_cost_ratio_pct": normalize_pct(funding_cost_ratio),
        }

        def display_pct(value):
            if value is None:
                return "--"
            return f"{value:.2f}%"

        narrative_lines = [
            f"這是一位偏{style}的交易者，近30日收益約 {display_pct(metrics_payload['month_return_pct'])}，最大回撤約 {display_pct(metrics_payload['month_drawdown_pct'])}，勝率約 {display_pct(metrics_payload['win_rate_pct'])}。",
        ]
        highlights = []
        if metrics_payload["week_return_pct"] is not None:
            highlights.append(f"收益動能：近7日收益率 {display_pct(metrics_payload['week_return_pct'])}，30日收益 {display_pct(metrics_payload['month_return_pct'])}。")
        if metrics_payload["funding_cost_ratio_pct"] is not None:
            ratio = metrics_payload["funding_cost_ratio_pct"]
            hints = "資金費控制得宜" if ratio <= 5 else "需注意資金費成本"
            highlights.append(f"成本結構：資金費佔比 {display_pct(ratio)}，{hints}。")
        if metrics_payload["trades_30d"]:
            highlights.append(
                f"交易節奏：近30日交易 {metrics_payload['trades_30d']} 筆，平均單筆盈虧約 {float(avg_pnl):.2f} USDC。"
            )
        if not highlights:
            highlights.append("尚無足夠歷史數據，建議持續觀察。")
        narrative = "\n".join(narrative_lines + ["", "重點觀察："] + [f"{idx+1}️⃣ {text}" for idx, text in enumerate(highlights)]) + f"\n\nAI 建議：{suggestion}"

        analysis = AIAnalysis(
            wallet_address=address,
            version=version,
            score=score,
            style=style,
            strengths="\n".join(strengths) if strengths else "暂无突出优势",
            risks="\n".join(risks) if risks else "风险水平可控",
            suggestion=suggestion,
            follow_ratio=follow_ratio,
            narrative=narrative,
            metrics=json.dumps(metrics_payload),
        )
        with write_lock:
            with session_scope() as write_session:
                write_session.add(analysis)
                write_session.flush()
                write_session.refresh(analysis)

        apply_ai_labels(address, analysis)
        tasks_service.log_ai_end(
            log_id,
            "success",
            response=f"score={analysis.score}, follow_ratio={analysis.follow_ratio}",
        )
        return analysis
    except Exception as exc:
        tasks_service.log_ai_end(log_id, "failed", error=str(exc))
        raise


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
    with write_lock:
        with session_scope() as session:
            config = session.execute(select(AIConfig).limit(1)).scalar_one_or_none()
            if not config:
                config = AIConfig()
                session.add(config)
                session.flush()
                session.refresh(config)
            return config


def update_ai_config(**kwargs) -> AIConfig:
    with write_lock:
        with session_scope() as session:
            config = session.execute(select(AIConfig).limit(1)).scalar_one_or_none()
            if not config:
                config = AIConfig()
            for key, value in kwargs.items():
                setattr(config, key, value)
            session.add(config)
            session.flush()
            session.refresh(config)
            return config


def serialize_analysis(analysis: AIAnalysis) -> dict:
    data = {
        "wallet_address": analysis.wallet_address,
        "version": analysis.version,
        "score": float(analysis.score) if analysis.score is not None else None,
        "style": analysis.style,
        "strengths": analysis.strengths,
        "risks": analysis.risks,
        "suggestion": analysis.suggestion,
        "follow_ratio": float(analysis.follow_ratio) if analysis.follow_ratio is not None else None,
        "narrative": analysis.narrative,
        "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
    }
    if analysis.metrics:
        try:
            data["metrics"] = json.loads(analysis.metrics)
        except Exception:
            data["metrics"] = None
    return data


def apply_ai_labels(wallet_address: str, analysis: AIAnalysis) -> None:
    config = get_ai_config()
    if not config.label_mapping:
        return
    try:
        mapping = json.loads(config.label_mapping)
        tags_to_apply = []
        for rule in mapping:
            key = rule.get("field")
            op = rule.get("op", ">=")
            value = rule.get("value")
            tag_name = rule.get("tag")
            if not key or tag_name is None:
                continue
            ai_value = getattr(analysis, key, None)
            if ai_value is None:
                continue
            flag = False
            if op == ">=" and ai_value >= value:
                flag = True
            elif op == ">" and ai_value > value:
                flag = True
            elif op == "<=" and ai_value <= value:
                flag = True
            elif op == "<" and ai_value < value:
                flag = True
            elif op == "==" and ai_value == value:
                flag = True
            elif op == "style_in" and isinstance(value, list) and analysis.style in value:
                flag = True
            if flag:
                tags_to_apply.append(tag_name)
        if tags_to_apply:
            tag_service.ensure_tags_exist(tags_to_apply, origin="ai")
            tag_service.assign_tag_names(wallet_address, tags_to_apply, origin="ai")
    except Exception:
        pass
