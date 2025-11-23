from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"
    __table_args__ = (
        UniqueConstraint("address", name="uq_wallet_address"),
    )

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(64), nullable=False, index=True)
    status = Column(String(32), default="imported", nullable=False)
    tags = Column(Text, default="[]")
    source = Column(String(32), default="manual")
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
