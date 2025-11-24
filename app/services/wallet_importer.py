from __future__ import annotations

import json
from datetime import datetime
from typing import List

from sqlalchemy import select

from app.core.database import session_scope, engine
from app.models import Wallet, WalletImportRecord
from app.schemas.wallets import WalletImportRequest, WalletImportResponse, WalletImportResult
from app.services import task_queue

_IMPORT_TABLE_READY = False


def _ensure_import_table_exists() -> None:
    global _IMPORT_TABLE_READY
    if _IMPORT_TABLE_READY:
        return
    WalletImportRecord.__table__.create(bind=engine, checkfirst=True)
    _IMPORT_TABLE_READY = True


def import_wallets(payload: WalletImportRequest, created_by: str | None = None) -> WalletImportResponse:
    """Persist wallet records and mark for downstream sync."""
    _ensure_import_table_exists()
    seen = set()
    results: List[dict] = []
    imported = 0
    new_wallet_indices: List[int] = []

    created_ts = datetime.utcnow()
    with session_scope() as session:
        record = WalletImportRecord(
            source=payload.source,
            tag_list=",".join(payload.tags or []),
            created_by=created_by,
            created_at=created_ts,
        )
        session.add(record)
        for addr in payload.addresses:
            if not payload.allow_duplicates and addr in seen:
                results.append(
                    {"address": addr, "status": "skipped", "message": "duplicate in request", "tags_applied": []}
                )
                continue
            seen.add(addr)

            if payload.dry_run:
                results.append(
                    {"address": addr, "status": "dry-run", "tags_applied": list(payload.tags or [])}
                )
                imported += 1
                continue

            existing = session.execute(select(Wallet).where(Wallet.address == addr)).scalar_one_or_none()
            if existing:
                results.append(
                    {"address": addr, "status": "exists", "message": "already imported", "tags_applied": []}
                )
                continue

            wallet = Wallet(
                address=addr,
                status="imported",
                tags=json.dumps(payload.tags or []),
                source=payload.source,
            )
            session.add(wallet)
            results.append(
                {"address": addr, "status": "imported", "tags_applied": list(payload.tags or [])}
            )
            imported += 1
            new_wallet_indices.append(len(results) - 1)

    for idx in new_wallet_indices:
        entry = results[idx]
        address = entry["address"]
        try:
            job_id = task_queue.enqueue_wallet_sync(address, scheduled_by=payload.source or "import")
            entry["job_id"] = job_id
        except Exception as exc:
            entry["message"] = f"sync enqueue failed: {exc}"

    skipped = sum(1 for r in results if r["status"] in {"skipped", "exists"})

    return WalletImportResponse(
        requested=len(payload.addresses),
        imported=imported,
        skipped=skipped,
        dry_run=payload.dry_run,
        results=[WalletImportResult(**item) for item in results],
        source=payload.source,
        tags=payload.tags,
        created_by=created_by,
        created_at=created_ts.isoformat(),
    )
