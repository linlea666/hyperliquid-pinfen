from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text

from app.core.database import Base


class TaskRecord(Base):
    __tablename__ = "task_records"

    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(String(64), nullable=False)
    status = Column(String(32), default="pending")
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WalletProcessingLog(Base):
    __tablename__ = "wallet_processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(64), index=True, nullable=False)
    stage = Column(String(32), nullable=False)  # sync | score | ai
    status = Column(String(32), default="pending")
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    attempt = Column(Integer, default=1)
    scheduled_by = Column(String(32), default="system")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AILog(Base):
    __tablename__ = "ai_logs"

    id = Column(Integer, primary_key=True, index=True)
    wallet_address = Column(String(64), index=True, nullable=False)
    status = Column(String(32), default="running")
    provider = Column(String(32), default="deepseek")
    model = Column(String(128))
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    tokens_used = Column(Integer, default=0)
    cost = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)


class NotificationTemplate(Base):
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    channel = Column(String(32), default="email")
    subject = Column(String(256), nullable=True)
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NotificationSubscription(Base):
    __tablename__ = "notification_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(128), nullable=False)
    template_id = Column(Integer, nullable=False)
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, nullable=False)
    recipient = Column(String(128), nullable=False)
    channel = Column(String(32), default="email")
    status = Column(String(32), default="pending")
    attempts = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class ScheduleJob(Base):
    __tablename__ = "schedule_jobs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    job_type = Column(String(64), nullable=False)  # e.g., leaderboard_run_all, wallet_sync
    cron = Column(String(64), nullable=False)  # cron expression
    payload = Column(Text, nullable=True)
    enabled = Column(Integer, default=1)
    next_run_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
