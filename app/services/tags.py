import json
from typing import List, Optional

from sqlalchemy import Select, and_, select

from app.core.database import session_scope
from app.models import Tag, WalletTag


def list_tags(tag_type: Optional[str] = None) -> List[Tag]:
    with session_scope() as session:
        stmt: Select[Tag] = select(Tag)
        if tag_type:
            stmt = stmt.where(Tag.type == tag_type)
        stmt = stmt.order_by(Tag.name)
        return session.execute(stmt).scalars().all()


def create_tag(name: str, tag_type: str, color: str, icon: Optional[str], description: Optional[str], rule_json: Optional[dict], parent_id: Optional[int]) -> Tag:
    with session_scope() as session:
        tag = Tag(
            name=name,
            type=tag_type,
            color=color,
            icon=icon,
            description=description,
            parent_id=parent_id,
            rule_json=json.dumps(rule_json) if rule_json else None,
        )
        session.add(tag)
        session.flush()
        session.refresh(tag)
        return tag


def assign_tags(wallet_address: str, tag_ids: List[int]) -> List[WalletTag]:
    with session_scope() as session:
        session.query(WalletTag).filter(WalletTag.wallet_address == wallet_address).delete()
        if not tag_ids:
            return []
        tags = session.execute(select(Tag).where(Tag.id.in_(tag_ids))).scalars().all()
        wallet_tags = []
        for tag in tags:
            wt = WalletTag(wallet_address=wallet_address, tag_id=tag.id)
            session.add(wt)
            wallet_tags.append(wt)
        session.flush()
        return wallet_tags


def wallet_tags(wallet_address: str) -> List[Tag]:
    with session_scope() as session:
        stmt = (
            select(Tag)
            .join(WalletTag, WalletTag.tag_id == Tag.id)
            .where(WalletTag.wallet_address == wallet_address)
            .order_by(Tag.name)
        )
        return session.execute(stmt).scalars().all()
