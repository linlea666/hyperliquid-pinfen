from datetime import datetime
from sqlalchemy import BigInteger, Column, DateTime, Integer, Numeric, String, UniqueConstraint

from app.core.database import Base


class WalletMetric(Base):
    __tablename__ = "wallet_metrics"
    __table_args__ = (
        UniqueConstraint("user", "as_of", name="uq_wallet_metrics_user_asof"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    as_of = Column(BigInteger, nullable=False, index=True)
    trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_rate = Column(Numeric(38, 18))
    total_pnl = Column(Numeric(38, 18))
    total_fees = Column(Numeric(38, 18))
    volume = Column(Numeric(38, 18))
    max_drawdown = Column(Numeric(38, 18))
    avg_pnl = Column(Numeric(38, 18))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WalletScore(Base):
    __tablename__ = "wallet_scores"
    __table_args__ = (
        UniqueConstraint("user", "as_of", name="uq_wallet_scores_user_asof"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String(64), index=True, nullable=False)
    as_of = Column(BigInteger, nullable=False, index=True)
    score = Column(Numeric(5, 2))
    level = Column(String(8))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    metrics_id = Column(Integer)
