from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), nullable=False)
    type = Column(String(16), default="user")  # system | ai | user
    color = Column(String(16), default="#7c3aed")
    icon = Column(String(32), nullable=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("tags.id"), nullable=True)
    rule_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    parent = relationship("Tag", remote_side=[id], backref="children")


class WalletTag(Base):
    __tablename__ = "wallet_tags"
    __table_args__ = (UniqueConstraint("wallet_address", "tag_id", name="uq_wallet_tag"),)

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(64), index=True, nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tag = relationship("Tag")
