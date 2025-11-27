from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings


def _wallet_dir(address: str) -> Path:
    settings = get_settings()
    target = settings.cache_dir / address.lower()
    target.mkdir(parents=True, exist_ok=True)
    return target


def append_events(address: str, kind: str, events: list[Dict[str, Any]]) -> None:
    """Append raw events to `<cache>/<wallet>/<kind>.jsonl`."""
    if not events:
        return
    path = _wallet_dir(address) / f"{kind}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        for item in events:
            fh.write(json.dumps(item, ensure_ascii=False))
            fh.write("\n")


def update_metadata(address: str, **fields: Any) -> None:
    if not fields:
        return
    meta_path = _wallet_dir(address) / "meta.json"
    data: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            data = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    data.update(fields)
    meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_json(address: str, filename: str, payload: Any) -> None:
    path = _wallet_dir(address) / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
