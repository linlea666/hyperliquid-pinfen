from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from app.core.database import Base


class PortfolioSeries(Base):
    __tablename__ = "portfolio_series"
    __table_args__ = (
        UniqueConstraint("user", "interval", "ts", name="uq_portfolio_user_interval_ts"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    interval = Column(String(16), nullable=False, index=True)  # day/week/month/allTime/perpDay...
    ts = Column(BigInteger, nullable=False, index=True)
    account_value = Column(Numeric(38, 18))
    pnl = Column(Numeric(38, 18))
    vlm = Column(Numeric(38, 18))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
