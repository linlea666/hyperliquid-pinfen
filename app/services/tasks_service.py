import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func

from app.core.database import session_scope
from app.models import TaskRecord


def log_task_start(task_type: str, payload: Optional[dict] = None) -> int:
    with session_scope() as session:
        record = TaskRecord(
            task_type=task_type,
            status="running",
            payload=json.dumps(payload) if payload else None,
            started_at=datetime.utcnow(),
        )
        session.add(record)
        session.flush()
        return record.id


def log_task_end(task_id: int, status: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
    with session_scope() as session:
        record = session.get(TaskRecord, task_id)
        if not record:
            return
        record.status = status
        record.result = json.dumps(result) if result else None
        record.error = error
        record.finished_at = datetime.utcnow()
        session.add(record)


def list_tasks(limit: int = 50, offset: int = 0, status: Optional[str] = None, task_type: Optional[str] = None) -> List[TaskRecord]:
    with session_scope() as session:
        stmt = select(TaskRecord).order_by(TaskRecord.created_at.desc()).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(TaskRecord.status == status)
        if task_type:
            stmt = stmt.where(TaskRecord.task_type == task_type)
        return session.execute(stmt).scalars().all()


def stats() -> dict:
    with session_scope() as session:
        total = session.execute(select(func.count()).select_from(TaskRecord)).scalar_one()
        running = session.execute(
            select(func.count()).select_from(TaskRecord).where(TaskRecord.status == "running")
        ).scalar_one()
        failed = session.execute(
            select(func.count()).select_from(TaskRecord).where(TaskRecord.status == "failed")
        ).scalar_one()
    return {"total": total, "running": running, "failed": failed}
