import json
from typing import Any, Dict

from app.services import admin as admin_service

CONFIG_KEY = "processing.settings"

DEFAULT_PROCESSING_CONFIG: Dict[str, Any] = {
    "max_parallel_sync": 3,
    "max_parallel_score": 3,
    "retry_limit": 3,
    "retry_delay_seconds": 600,
    "rescore_period_days": 7,
    "rescore_trigger_pct": 5.0,
    "ai_period_days": 30,
}


def _with_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = DEFAULT_PROCESSING_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def get_processing_config() -> Dict[str, Any]:
    value = admin_service.get_config(CONFIG_KEY)
    if not value:
        return DEFAULT_PROCESSING_CONFIG
    try:
        loaded = json.loads(value)
        if not isinstance(loaded, dict):
            raise ValueError
        return _with_defaults(loaded)
    except ValueError:
        return DEFAULT_PROCESSING_CONFIG


def save_processing_config(config: Dict[str, Any]) -> None:
    validate_processing_config(config)
    admin_service.upsert_config(CONFIG_KEY, json.dumps(config), "Processing pipeline settings")


def validate_processing_config(config: Dict[str, Any]) -> None:
    merged = _with_defaults(config)
    for key in ("max_parallel_sync", "max_parallel_score", "retry_limit", "rescore_period_days", "ai_period_days"):
        value = merged.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("retry_delay_seconds",):
        value = merged.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")
    trigger = merged.get("rescore_trigger_pct")
    if not isinstance(trigger, (int, float)) or trigger < 0:
        raise ValueError("rescore_trigger_pct must be >= 0")
