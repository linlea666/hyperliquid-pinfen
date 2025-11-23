from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base


class LedgerEvent(Base):
    __tablename__ = "ledger_events"
    __table_args__ = (
        UniqueConstraint("user", "time_ms", "hash", name="uq_ledger_user_time_hash"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    time_ms = Column(BigInteger, index=True, nullable=False)
    hash = Column(String(128), nullable=False)
    delta_type = Column(String(32), index=True, nullable=False)
    vault = Column(String(128))
    token = Column(String(64))
    amount = Column(Numeric(38, 18))
    usdc_value = Column(Numeric(38, 18))
    fee = Column(Numeric(38, 18))
    native_token_fee = Column(Numeric(38, 18))
    nonce = Column(BigInteger)
    basis = Column(Numeric(38, 18))
    commission = Column(Numeric(38, 18))
    closing_cost = Column(Numeric(38, 18))
    net_withdrawn_usd = Column(Numeric(38, 18))
    source_dex = Column(String(32))
    destination_dex = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_json = Column(Text, nullable=False)


class FetchCursor(Base):
    __tablename__ = "fetch_cursors"
    __table_args__ = (
        UniqueConstraint("user", "cursor_type", name="uq_cursor_user_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), nullable=False, index=True)
    cursor_type = Column(String(32), nullable=False)
    last_time_ms = Column(BigInteger, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
