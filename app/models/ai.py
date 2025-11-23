from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text, UniqueConstraint

from app.core.database import Base


class AIAnalysis(Base):
    __tablename__ = "ai_analysis"
    __table_args__ = (UniqueConstraint("wallet_address", "version", name="uq_ai_wallet_version"),)

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(64), nullable=False, index=True)
    version = Column(String(32), default="v1")
    score = Column(Numeric(5, 2))
    style = Column(String(64))
    strengths = Column(Text)
    risks = Column(Text)
    suggestion = Column(Text)
    follow_ratio = Column(Numeric(5, 2))
    status = Column(String(32), default="completed")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
