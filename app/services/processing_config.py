import json
from typing import Any, Dict, Tuple, List

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
    "scope_type": "all",
    "scope_recent_days": 7,
    "scope_tag": "",
    "batch_size": 50,
    "batch_interval_seconds": 600,
    "request_rate_per_min": 120,
    "sync_cooldown_days": 1,
    "score_cooldown_days": 7,
    "ai_cooldown_days": 30,
    "portfolio_refresh_hours": 24,
}

DEFAULT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "key": "balanced",
        "name": "均衡策略",
        "description": "关注最近 7 天导入的钱包，每批 50 个，10 分钟处理一次",
        "overrides": {
            "scope_type": "recent",
            "scope_recent_days": 7,
            "batch_size": 50,
            "batch_interval_seconds": 600,
            "request_rate_per_min": 120,
        },
    },
    {
        "key": "fast-track",
        "name": "快速跟踪",
        "description": "仅处理今日导入，缩短批次间隔，适合高优钱包",
        "overrides": {
            "scope_type": "today",
            "batch_size": 80,
            "batch_interval_seconds": 300,
            "request_rate_per_min": 200,
            "sync_cooldown_days": 1,
            "score_cooldown_days": 3,
        },
    },
    {
        "key": "conservative",
        "name": "资源友好",
        "description": "覆盖全部钱包但批次小、间隔长，适合低频巡检",
        "overrides": {
            "scope_type": "all",
            "batch_size": 30,
            "batch_interval_seconds": 1200,
            "request_rate_per_min": 90,
            "sync_cooldown_days": 2,
            "score_cooldown_days": 10,
        },
    },
]

DEFAULT_ACTIVE_TEMPLATE = "balanced"


def _with_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    merged = DEFAULT_PROCESSING_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k in merged})
    return merged


def _load_payload() -> Tuple[Dict[str, Any], List[Dict[str, Any]], str]:
    value = admin_service.get_config(CONFIG_KEY)
    if not value:
        return DEFAULT_PROCESSING_CONFIG, DEFAULT_TEMPLATES, DEFAULT_ACTIVE_TEMPLATE
    try:
        loaded = json.loads(value)
        if isinstance(loaded, dict) and "settings" in loaded:
            settings = _with_defaults(loaded.get("settings", {}))
            templates = loaded.get("templates") or DEFAULT_TEMPLATES
            active = loaded.get("active_template") or DEFAULT_ACTIVE_TEMPLATE
        elif isinstance(loaded, dict):
            settings = _with_defaults(loaded)
            templates = DEFAULT_TEMPLATES
            active = DEFAULT_ACTIVE_TEMPLATE
        else:
            raise ValueError
        return settings, templates, active
    except ValueError:
        return DEFAULT_PROCESSING_CONFIG, DEFAULT_TEMPLATES, DEFAULT_ACTIVE_TEMPLATE


def get_processing_config() -> Dict[str, Any]:
    settings, _, _ = _load_payload()
    return settings


def get_processing_bundle() -> Dict[str, Any]:
    settings, templates, active = _load_payload()
    return {"config": settings, "templates": templates, "active_template": active}


def save_processing_config(config: Dict[str, Any], active_template: str | None = None) -> None:
    validate_processing_config(config)
    _, templates, current_active = _load_payload()
    payload = {
        "settings": _with_defaults(config),
        "templates": templates,
        "active_template": active_template or current_active or DEFAULT_ACTIVE_TEMPLATE,
    }
    admin_service.upsert_config(CONFIG_KEY, json.dumps(payload), "Processing pipeline settings")


def validate_processing_config(config: Dict[str, Any]) -> None:
    merged = _with_defaults(config)
    for key in (
        "max_parallel_sync",
        "max_parallel_score",
        "retry_limit",
        "rescore_period_days",
        "ai_period_days",
        "batch_size",
        "scope_recent_days",
        "request_rate_per_min",
        "sync_cooldown_days",
        "score_cooldown_days",
        "ai_cooldown_days",
        "portfolio_refresh_hours",
    ):
        value = merged.get(key)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
    for key in ("retry_delay_seconds", "batch_interval_seconds"):
        value = merged.get(key)
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")
    trigger = merged.get("rescore_trigger_pct")
    if not isinstance(trigger, (int, float)) or trigger < 0:
        raise ValueError("rescore_trigger_pct must be >= 0")
    scope_type = merged.get("scope_type")
    if scope_type not in {"all", "today", "recent", "tag"}:
        raise ValueError("scope_type invalid")
