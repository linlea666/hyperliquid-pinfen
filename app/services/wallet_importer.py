import json
from typing import List

from sqlalchemy import select

from app.core.database import session_scope
from app.models import Wallet
from app.schemas.wallets import WalletImportRequest, WalletImportResponse, WalletImportResult


def import_wallets(payload: WalletImportRequest) -> WalletImportResponse:
    """Persist wallet records and mark for downstream sync."""
    seen = set()
    results: List[WalletImportResult] = []
    imported = 0

    with session_scope() as session:
        for addr in payload.addresses:
            if not payload.allow_duplicates and addr in seen:
                results.append(
                    WalletImportResult(address=addr, status="skipped", message="duplicate in request")
                )
                continue
            seen.add(addr)

            if payload.dry_run:
                results.append(
                    WalletImportResult(address=addr, status="dry-run", tags_applied=payload.tags)
                )
                imported += 1
                continue

            existing = session.execute(select(Wallet).where(Wallet.address == addr)).scalar_one_or_none()
            if existing:
                results.append(
                    WalletImportResult(address=addr, status="exists", message="already imported")
                )
                continue

            wallet = Wallet(
                address=addr,
                status="imported",
                tags=json.dumps(payload.tags or []),
                source=payload.source,
            )
            session.add(wallet)
            results.append(WalletImportResult(address=addr, status="imported", tags_applied=payload.tags))
            imported += 1

    skipped = sum(1 for r in results if r.status in {"skipped", "exists"})

    return WalletImportResponse(
        requested=len(payload.addresses),
        imported=imported,
        skipped=skipped,
        dry_run=payload.dry_run,
        results=results,
    )
