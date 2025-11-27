import json
from typing import Any, Dict, List

from app.services import admin as admin_service

CONFIG_KEY = "scoring.config"

DEFAULT_SCORING_CONFIG: Dict[str, Any] = {
    "dimensions": [
        {
            "key": "return",
            "name": "收益能力",
            "weight": 30,
            "indicators": [
                {"field": "total_pnl", "min": -100000, "max": 100000, "higher_is_better": True, "weight": 1},
                {"field": "avg_pnl", "min": -1000, "max": 1000, "higher_is_better": True, "weight": 1},
            ],
        },
        {
            "key": "risk",
            "name": "风险控制",
            "weight": 20,
            "indicators": [
                {"field": "max_drawdown", "min": 0, "max": 100000, "higher_is_better": False, "weight": 1},
            ],
        },
        {
            "key": "risk_adjusted",
            "name": "风险调整收益",
            "weight": 15,
            "indicators": [
                {"field": "win_rate", "min": 0, "max": 1, "higher_is_better": True, "weight": 1},
            ],
        },
        {
            "key": "trade_quality",
            "name": "交易质量",
            "weight": 15,
            "indicators": [
                {"field": "trades", "min": 0, "max": 500, "higher_is_better": True, "weight": 1},
            ],
        },
        {
            "key": "stability",
            "name": "稳定性",
            "weight": 10,
            "indicators": [
                {"field": "equity_stability", "min": 0, "max": 1, "higher_is_better": True, "weight": 1},
            ],
        },
        {
            "key": "capital_efficiency",
            "name": "资金效率",
            "weight": 10,
            "indicators": [
                {"field": "capital_efficiency", "min": 0, "max": 1, "higher_is_better": True, "weight": 1},
            ],
        },
        {
            "key": "cost",
            "name": "成本控制",
            "weight": 10,
            "indicators": [
                {"field": "funding_cost_ratio", "min": 0, "max": 1, "higher_is_better": False, "weight": 1},
                {"field": "effective_fee_cross", "min": 0, "max": 0.002, "higher_is_better": False, "weight": 1},
            ],
        },
        {
            "key": "portfolio",
            "name": "官方表现",
            "weight": 15,
            "indicators": [
                {"field": "portfolio_return_30d", "min": -0.5, "max": 0.5, "higher_is_better": True, "weight": 1},
                {"field": "portfolio_max_drawdown_30d", "min": 0, "max": 0.5, "higher_is_better": False, "weight": 1},
            ],
        },
    ],
    "levels": [
        {"level": "S", "min_score": 90},
        {"level": "A+", "min_score": 80},
        {"level": "A", "min_score": 70},
        {"level": "B", "min_score": 60},
        {"level": "C", "min_score": 0},
    ],
}


def get_scoring_config() -> Dict[str, Any]:
    value = admin_service.get_config(CONFIG_KEY)
    if not value:
        return DEFAULT_SCORING_CONFIG
    try:
        config = json.loads(value)
        if not isinstance(config, dict):
            raise ValueError
        return config
    except ValueError:
        return DEFAULT_SCORING_CONFIG


def save_scoring_config(config: Dict[str, Any]) -> None:
    validate_config(config)
    admin_service.upsert_config(CONFIG_KEY, json.dumps(config), "Scoring module configuration")


def validate_config(config: Dict[str, Any]) -> None:
    dimensions = config.get("dimensions")
    if not dimensions or not isinstance(dimensions, list):
        raise ValueError("dimensions must be a non-empty list")
    total_weight = 0
    for dim in dimensions:
        if "key" not in dim or "weight" not in dim:
            raise ValueError("dimension requires key and weight")
        if dim["weight"] <= 0:
            raise ValueError("dimension weight must be > 0")
        total_weight += dim["weight"]
        indicators = dim.get("indicators") or []
        for indicator in indicators:
            if indicator.get("min") is None or indicator.get("max") is None:
                raise ValueError("indicator requires min and max")
            if indicator["min"] >= indicator["max"]:
                raise ValueError("indicator min must be < max")
    if total_weight <= 0:
        raise ValueError("sum of dimension weights must be > 0")

    levels = config.get("levels")
    if not levels or not isinstance(levels, list):
        raise ValueError("levels must be a list")
    for level in levels:
        if "level" not in level or "min_score" not in level:
            raise ValueError("each level needs level and min_score")
