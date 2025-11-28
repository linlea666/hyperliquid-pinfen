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


class AIConfig(Base):
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, index=True)
    is_enabled = Column(Integer, default=1)
    provider = Column(String(32), default="deepseek")
    api_key = Column(String(256), nullable=True)
    model = Column(String(128), default="deepseek-chat")
    base_url = Column(String(256), nullable=True)
    max_tokens = Column(Integer, default=1024)
    temperature = Column(Numeric(4, 2), default=0.3)
    rate_limit_per_minute = Column(Integer, default=60)
    cooldown_minutes = Column(Integer, default=60)
    prompt_style = Column(Text, nullable=True)
    prompt_strength = Column(Text, nullable=True)
    prompt_risk = Column(Text, nullable=True)
    prompt_suggestion = Column(Text, nullable=True)
    label_mapping = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
