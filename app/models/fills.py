from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint, Boolean

from app.core.database import Base


class Fill(Base):
    __tablename__ = "fills"
    __table_args__ = (
        UniqueConstraint("user", "time_ms", "tid", "oid", name="uq_fills_user_time_tid_oid"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    time_ms = Column(BigInteger, index=True, nullable=False)
    coin = Column(String(64), index=True, nullable=False)
    side = Column(String(8))
    dir = Column(String(32))
    px = Column(Numeric(38, 18))
    sz = Column(Numeric(38, 18))
    fee = Column(Numeric(38, 18))
    fee_token = Column(String(32))
    crossed = Column(Boolean)
    closed_pnl = Column(Numeric(38, 18))
    start_position = Column(Numeric(38, 18))
    hash = Column(String(128))
    oid = Column(BigInteger)
    tid = Column(BigInteger)
    builder_fee = Column(Numeric(38, 18))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_json = Column(Text, nullable=False)
