import json
from typing import Dict, List, Optional

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


def update_tag(tag_id: int, payload: Dict) -> Tag:
    with session_scope() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise ValueError("Tag not found")
        for key, value in payload.items():
            if key == "rule_json":
                setattr(tag, "rule_json", json.dumps(value) if value else None)
            else:
                setattr(tag, key, value)
        session.add(tag)
        session.flush()
        session.refresh(tag)
        return tag


def delete_tag(tag_id: int) -> None:
    with session_scope() as session:
        tag = session.get(Tag, tag_id)
        if not tag:
            raise ValueError("Tag not found")
        session.query(WalletTag).filter(WalletTag.tag_id == tag_id).delete()
        session.delete(tag)


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


def ensure_tags_exist(tag_names: List[str], origin: str = "ai") -> List[Tag]:
    with session_scope() as session:
        existing = session.execute(select(Tag).where(Tag.name.in_(tag_names))).scalars().all()
        name_to_tag = {tag.name: tag for tag in existing}
        for name in tag_names:
            if name not in name_to_tag:
                tag = Tag(name=name, type=origin, color="#22d3ee")
                session.add(tag)
                session.flush()
                session.refresh(tag)
                name_to_tag[name] = tag
        return list(name_to_tag.values())


def assign_tag_names(wallet_address: str, tag_names: List[str], origin: str = "ai") -> None:
    tags = ensure_tags_exist(tag_names, origin=origin)
    assign_tags(wallet_address, [tag.id for tag in tags])


def wallet_tags(wallet_address: str) -> List[Tag]:
    with session_scope() as session:
        stmt = (
            select(Tag)
            .join(WalletTag, WalletTag.tag_id == Tag.id)
            .where(WalletTag.wallet_address == wallet_address)
            .order_by(Tag.name)
        )
        return session.execute(stmt).scalars().all()
