from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base


class PositionSnapshot(Base):
    __tablename__ = "positions_snapshot"
    __table_args__ = (
        UniqueConstraint("user", "time_ms", "coin", name="uq_position_user_time_coin"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), nullable=False, index=True)
    time_ms = Column(BigInteger, nullable=False, index=True)
    coin = Column(String(64), nullable=False, index=True)
    szi = Column(Numeric(38, 18))
    entry_px = Column(Numeric(38, 18))
    pos_value = Column(Numeric(38, 18))
    unrealized_pnl = Column(Numeric(38, 18))
    roe = Column(Numeric(38, 18))
    liq_px = Column(Numeric(38, 18))
    margin_used = Column(Numeric(38, 18))
    leverage_type = Column(String(16))
    leverage_value = Column(Numeric(38, 18))
    max_leverage = Column(Numeric(38, 18))
    cum_funding_all = Column(Numeric(38, 18))
    cum_funding_open = Column(Numeric(38, 18))
    cum_funding_change = Column(Numeric(38, 18))
    summary_account_value = Column(Numeric(38, 18))
    summary_ntl_pos = Column(Numeric(38, 18))
    withdrawable = Column(Numeric(38, 18))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_json = Column(Text, nullable=False)
