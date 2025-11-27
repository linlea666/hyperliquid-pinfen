from sqlalchemy import select, text

from app.core.database import session_scope, engine
from app.core.security import hash_password
from app.models import User, Leaderboard
import json

PROCESSING_COLUMNS = {
    "wallets": {
        "sync_status": "TEXT DEFAULT 'pending'",
        "score_status": "TEXT DEFAULT 'pending'",
        "ai_status": "TEXT DEFAULT 'pending'",
        "last_score_at": "DATETIME",
        "last_ai_at": "DATETIME",
        "next_sync_due": "DATETIME",
        "next_score_due": "DATETIME",
        "next_ai_due": "DATETIME",
        "last_error": "TEXT",
        "note": "TEXT",
        "first_trade_time": "DATETIME",
    },
    "wallet_metrics": {
        "details": "TEXT",
    },
    "wallet_scores": {
        "dimension_scores": "TEXT",
    },
}

LEADERBOARD_PRESETS = [
    {
        "name": "稳健收益榜",
        "description": "低回撤、高胜率的钱包",
        "icon": "🛡️",
        "style": "table",
        "accent_color": "#0ea5e9",
        "filters": [
            {"source": "metric", "field": "win_rate", "op": ">=", "value": 0.55},
            {"source": "portfolio", "period": "month", "field": "max_drawdown_pct", "op": "<=", "value": 0.2},
        ],
        "sort_key": "portfolio_month_return",
        "sort_order": "desc",
        "period": "month",
    },
    {
        "name": "趋势交易榜",
        "description": "抓住趋势、收益稳定",
        "icon": "📈",
        "style": "table",
        "accent_color": "#f97316",
        "filters": [
            {"source": "metric", "field": "trades", "op": ">=", "value": 30},
            {"source": "portfolio", "period": "month", "field": "return_pct", "op": ">=", "value": 0.1},
        ],
        "sort_key": "portfolio_month_return",
        "sort_order": "desc",
        "period": "month",
    },
    {
        "name": "资金效率榜",
        "description": "单位资金收益高、回报效率强",
        "icon": "⚡",
        "style": "card",
        "accent_color": "#10b981",
        "filters": [
            {"source": "metric", "field": "capital_efficiency", "op": ">=", "value": 0.5},
        ],
        "sort_key": "capital_efficiency",
        "sort_order": "desc",
        "period": "all",
    },
    {
        "name": "短线高手榜",
        "description": "高频交易、胜率优秀",
        "icon": "⚔️",
        "style": "table",
        "accent_color": "#a855f7",
        "filters": [
            {"source": "metric", "field": "trades", "op": ">=", "value": 80},
            {"source": "metric", "field": "win_rate", "op": ">=", "value": 0.6},
        ],
        "sort_key": "win_rate",
        "sort_order": "desc",
        "period": "month",
    },
    {
        "name": "潜力新星榜",
        "description": "近期表现亮眼的新钱包",
        "icon": "🌠",
        "style": "card",
        "accent_color": "#f97316",
        "filters": [
            {"source": "metric", "field": "trades", "op": ">=", "value": 20},
            {"source": "portfolio", "period": "week", "field": "return_pct", "op": ">=", "value": 0.05},
        ],
        "sort_key": "portfolio_week_return",
        "sort_order": "desc",
        "period": "week",
    },
    {
        "name": "资金费套利榜",
        "description": "靠资金费稳定收益的账户",
        "icon": "💰",
        "style": "table",
        "accent_color": "#facc15",
        "filters": [
            {"source": "metric", "field": "funding_cost_ratio", "op": "<=", "value": 0.05},
        ],
        "sort_key": "funding_cost_ratio",
        "sort_order": "asc",
        "period": "all",
    },
    {
        "name": "抗波动榜",
        "description": "回撤低、资产稳健",
        "icon": "🏔️",
        "style": "table",
        "accent_color": "#0ea5e9",
        "filters": [
            {"source": "portfolio", "period": "month", "field": "max_drawdown_pct", "op": "<=", "value": 0.15},
        ],
        "sort_key": "portfolio_month_drawdown",
        "sort_order": "asc",
        "period": "month",
    },
]


def ensure_processing_schema() -> None:
    """Ensure new processing columns exist when using SQLite without migrations."""
    with engine.begin() as conn:
        for table, columns in PROCESSING_COLUMNS.items():
            existing_columns = {row[1] for row in conn.execute(text(f"PRAGMA table_info('{table}')"))}
            for column, ddl in columns.items():
                if column not in existing_columns:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def ensure_default_admin():
    """Create default admin account if none exists."""
    with session_scope() as session:
        existing = session.execute(select(User)).scalars().first()
        if existing:
            return
        password_hash, salt = hash_password("admin888")
        user = User(
            email="admin@example.com",
            name="Admin",
            password_hash=password_hash,
            password_salt=salt,
            require_2fa=0,
            status="active",
        )
        session.add(user)


def ensure_default_leaderboards():
    with session_scope() as session:
        existing_names = {
            name for (name,) in session.execute(select(Leaderboard.name)).all()
        }
        for preset in LEADERBOARD_PRESETS:
            if preset["name"] in existing_names:
                continue
            lb = Leaderboard(
                name=preset["name"],
                type="preset",
                description=preset.get("description"),
                icon=preset.get("icon"),
                style=preset.get("style", "table"),
                accent_color=preset.get("accent_color", "#7c3aed"),
                badge=preset.get("badge"),
                filters=json.dumps(preset.get("filters")),
                sort_key=preset.get("sort_key", "total_pnl"),
                sort_order=preset.get("sort_order", "desc"),
                period=preset.get("period", "month"),
                is_public=1,
            )
            session.add(lb)
