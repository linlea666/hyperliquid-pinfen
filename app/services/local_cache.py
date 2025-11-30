from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def read_events(
    address: str,
    kind: str,
    *,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
) -> List[Dict[str, Any]]:
    path = _wallet_dir(address) / f"{kind}.jsonl"
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = data.get("time_ms") or data.get("time") or data.get("timestamp")
            try:
                ts_int = int(ts) if ts is not None else None
            except Exception:
                ts_int = None
            if ts_int is not None:
                if start_time is not None and ts_int < start_time:
                    continue
                if end_time is not None and ts_int > end_time:
                    continue
                data.setdefault("time_ms", ts_int)
            events.append(data)
    events.sort(key=lambda item: item.get("time_ms") or item.get("time") or 0, reverse=True)
    return events
