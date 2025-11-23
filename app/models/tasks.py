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
