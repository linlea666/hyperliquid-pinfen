from decimal import Decimal
from typing import Optional

from sqlalchemy import desc, select

from app.core.database import session_scope
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
@@
 def latest_analysis(address: str) -> Optional[AIAnalysis]:
@@
 def get_ai_config() -> AIConfig:
@@
 def update_ai_config(**kwargs) -> AIConfig:
@@
 
+def apply_ai_labels(wallet_address: str, analysis: AIAnalysis) -> None:
+    config = get_ai_config()
+    if not config.label_mapping:
+        return
+    try:
+        import json
+
+        mapping = json.loads(config.label_mapping)
+        tags_to_apply = []
+        for rule in mapping:
+            key = rule.get("field")
+            op = rule.get("op", ">=")
+            value = rule.get("value")
+            tag_name = rule.get("tag")
+            if not key or tag_name is None:
+                continue
+            ai_value = getattr(analysis, key, None)
+            if ai_value is None:
+                continue
+            flag = False
+            if op == ">=" and ai_value >= value:
+                flag = True
+            elif op == ">" and ai_value > value:
+                flag = True
+            elif op == "<=" and ai_value <= value:
+                flag = True
+            elif op == "<" and ai_value < value:
+                flag = True
+            elif op == "==" and ai_value == value:
+                flag = True
+            elif op == "style_in" and isinstance(value, list) and analysis.style in value:
+                flag = True
+            if flag:
+                tags_to_apply.append(tag_name)
+        if tags_to_apply:
+            tag_service.ensure_tags_exist(tags_to_apply, origin="ai")
+            tag_service.assign_tag_names(wallet_address, tags_to_apply, origin="ai")
+    except Exception:
+        pass
*** End Patch
