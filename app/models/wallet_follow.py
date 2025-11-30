from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint

from app.core.database import Base


class WalletFollow(Base):
    __tablename__ = "wallet_follows"
    __table_args__ = (
        UniqueConstraint("wallet_address", name="uq_wallet_follow_address"),
    )

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(64), nullable=False, index=True)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

