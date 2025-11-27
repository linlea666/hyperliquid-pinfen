from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Leaderboard(Base):
    __tablename__ = "leaderboards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(16), default="custom")  # preset | custom
    description = Column(Text)
    icon = Column(String(32))
    style = Column(String(16), default="table")  # table | card
    accent_color = Column(String(16), default="#7c3aed")
    badge = Column(String(32))
    filters = Column(Text, nullable=True)  # JSON string
    sort_key = Column(String(64), default="total_pnl")
    sort_order = Column(String(4), default="desc")
    period = Column(String(32), default="all")
    is_public = Column(Integer, default=1)
    result_limit = Column(Integer, default=20)
    auto_refresh_minutes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    results = relationship("LeaderboardResult", back_populates="leaderboard", cascade="all, delete-orphan")


class LeaderboardResult(Base):
    __tablename__ = "leaderboard_results"

    id = Column(Integer, primary_key=True, index=True)
    leaderboard_id = Column(Integer, ForeignKey("leaderboards.id"), nullable=False)
    wallet_address = Column(String(64), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    score = Column(Numeric(10, 4), nullable=True)
    snapshot_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    metrics = Column(Text, nullable=True)

    leaderboard = relationship("Leaderboard", back_populates="results")
