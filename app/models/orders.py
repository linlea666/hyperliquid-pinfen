from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base


class OrderHistory(Base):
    __tablename__ = "orders_history"
    __table_args__ = (
        UniqueConstraint("user", "time_ms", "oid", name="uq_orders_user_time_oid"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    time_ms = Column(BigInteger, nullable=False, index=True)
    coin = Column(String(64), index=True, nullable=False)
    side = Column(String(8))
    limit_px = Column(Numeric(38, 18))
    sz = Column(Numeric(38, 18))
    order_type = Column(String(32))
    tif = Column(String(32))
    oid = Column(BigInteger, nullable=True, index=True)
    reduce_only = Column(Integer)  # store as 0/1
    is_trigger = Column(Integer)  # store as 0/1
    trigger_px = Column(Numeric(38, 18))
    trigger_condition = Column(String(32))
    status = Column(String(32))
    status_ts = Column(BigInteger)
    cloid = Column(String(64))
    raw_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
