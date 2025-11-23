import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import and_, desc, func, select

from app.core.database import session_scope
from app.models import Fill, LedgerEvent, Wallet, WalletMetric, WalletScore, WalletTag, Tag


def _serialize_sa(obj):
    if not obj:
        return None
    data = obj.__dict__.copy()
    data.pop("_sa_instance_state", None)
    for key, value in list(data.items()):
        if isinstance(value, Decimal):
            data[key] = str(value)
        elif hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data


def update_sync_status(address: str) -> None:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if wallet:
            wallet.status = "synced"
            wallet.last_synced_at = datetime.utcnow()
            session.add(wallet)


def _latest_metric_map(session, addresses: List[str]) -> Dict[str, WalletMetric]:
    if not addresses:
        return {}
    subq = (
        select(
            WalletMetric.user.label("user"),
            func.max(WalletMetric.as_of).label("max_as_of"),
        )
        .where(WalletMetric.user.in_(addresses))
        .group_by(WalletMetric.user)
        .subquery()
    )
    rows = (
        session.execute(
            select(WalletMetric).join(
                subq,
                (WalletMetric.user == subq.c.user) & (WalletMetric.as_of == subq.c.max_as_of),
            )
        )
        .scalars()
        .all()
    )
    return {row.user: row for row in rows}


def _tags_map(session, addresses: List[str]) -> Dict[str, List[dict]]:
    if not addresses:
        return {}
    stmt = (
        select(WalletTag.wallet_address, Tag)
        .join(Tag, Tag.id == WalletTag.tag_id)
        .where(WalletTag.wallet_address.in_(addresses))
    )
    rows = session.execute(stmt).all()
    mapping: Dict[str, List[dict]] = {}
    for address, tag in rows:
        mapping.setdefault(address, []).append(
            {
                "id": tag.id,
                "name": tag.name,
                "type": tag.type,
                "color": tag.color,
                "icon": tag.icon,
            }
        )
    return mapping


def list_wallets(
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
):
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    conditions = []
    if status:
        conditions.append(Wallet.status == status)
    if search:
        like_pattern = f"%{search.lower()}%"
        conditions.append(func.lower(Wallet.address).like(like_pattern))
    if tag:
        conditions.append(Wallet.tags.like(f'%"{tag}"%'))

    with session_scope() as session:
        count_query = select(func.count()).select_from(Wallet)
        data_query = select(Wallet).order_by(desc(Wallet.created_at)).offset(offset).limit(limit)
        if conditions:
            predicate = and_(*conditions)
            count_query = count_query.where(predicate)
            data_query = data_query.where(predicate)
        total = session.execute(count_query).scalar_one()
        rows = session.execute(data_query).scalars().all()
        addresses = [row.address for row in rows]
        metrics_map = _latest_metric_map(session, addresses)
        tags_map = _tags_map(session, addresses)

    def serialize(wallet: Wallet) -> dict:
        tags = tags_map.get(wallet.address) or json.loads(wallet.tags) if wallet.tags else []
        metric = metrics_map.get(wallet.address)
        metric_dict = _serialize_sa(metric)
        return {
            "address": wallet.address,
            "status": wallet.status,
            "tags": tags,
            "source": wallet.source,
            "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
            "created_at": wallet.created_at.isoformat(),
            "metric": metric_dict,
        }

    return {"total": total, "items": [serialize(row) for row in rows]}


def get_wallet_detail(address: str) -> Optional[dict]:
    with session_scope() as session:
        wallet = session.execute(select(Wallet).where(Wallet.address == address)).scalar_one_or_none()
        if not wallet:
            return None
        metric_map = _latest_metric_map(session, [address])
        metric = metric_map.get(address)
        score = (
            session.execute(
                select(WalletScore)
                .where(WalletScore.user == address)
                .order_by(desc(WalletScore.as_of))
            )
            .scalars()
            .first()
        )
        tags_map = _tags_map(session, [address])
    data = {
        "address": wallet.address,
        "status": wallet.status,
        "tags": tags_map.get(address) or (json.loads(wallet.tags) if wallet.tags else []),
        "source": wallet.source,
        "last_synced_at": wallet.last_synced_at.isoformat() if wallet.last_synced_at else None,
        "created_at": wallet.created_at.isoformat(),
    }
    metric_dict = _serialize_sa(metric)
    score_dict = _serialize_sa(score)
    if metric_dict:
        data["metric"] = metric_dict
    if score_dict:
        data["score"] = score_dict
    return data


def get_wallet_overview() -> dict:
    with session_scope() as session:
        total_wallets = session.execute(select(func.count()).select_from(Wallet)).scalar_one()
        synced_wallets = (
            session.execute(select(func.count()).select_from(Wallet).where(Wallet.status == "synced")).scalar_one()
            if total_wallets
            else 0
        )
        ledger_events = session.execute(select(func.count()).select_from(LedgerEvent)).scalar_one()
        fills = session.execute(select(func.count()).select_from(Fill)).scalar_one()
        last_sync = (
            session.execute(select(func.max(Wallet.last_synced_at)).select_from(Wallet)).scalar_one()
        )
    return {
        "total_wallets": total_wallets,
        "synced_wallets": synced_wallets,
        "ledger_events": ledger_events,
        "fills": fills,
        "last_sync": last_sync.isoformat() if last_sync else None,
    }
