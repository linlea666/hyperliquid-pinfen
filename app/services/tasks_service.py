import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func

import time
from sqlalchemy.exc import OperationalError

from app.core.database import session_scope
from app.models import TaskRecord, AILog


def _with_retry(operation, retries: int = 3, delay: float = 0.2):
    last_exc: Optional[Exception] = None
    for attempt in range(retries):
        try:
            with session_scope() as session:
                return operation(session)
        except OperationalError as exc:
            last_exc = exc
            if attempt + 1 == retries:
                raise
            time.sleep(delay * (attempt + 1))
    if last_exc:
        raise last_exc


def log_task_start(task_type: str, payload: Optional[dict] = None) -> int:
    def operation(session):
        record = TaskRecord(
            task_type=task_type,
            status="running",
            payload=json.dumps(payload) if payload else None,
            started_at=datetime.utcnow(),
        )
        session.add(record)
        session.flush()
        return record.id

    return _with_retry(operation)


def log_task_end(task_id: int, status: str, result: Optional[dict] = None, error: Optional[str] = None) -> None:
    def operation(session):
        record = session.get(TaskRecord, task_id)
        if not record:
            return
        record.status = status
        record.result = json.dumps(result) if result else None
        record.error = error
        record.finished_at = datetime.utcnow()
        session.add(record)

    _with_retry(operation)


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


def log_ai_start(wallet_address: str, provider: str, model: str, prompt: Optional[str] = None) -> int:
    def operation(session):
        log = AILog(
            wallet_address=wallet_address,
            provider=provider,
            model=model,
            prompt=prompt,
            status="running",
        )
        session.add(log)
        session.flush()
        return log.id

    return _with_retry(operation)


def log_ai_end(
    log_id: int,
    status: str,
    *,
    response: Optional[str] = None,
    error: Optional[str] = None,
    tokens: int = 0,
    cost: Optional[str] = None,
) -> None:
    def operation(session):
        log = session.get(AILog, log_id)
        if not log:
            return
        log.status = status
        log.response = response
        log.error = error
        log.tokens_used = tokens
        log.cost = cost
        log.finished_at = datetime.utcnow()
        session.add(log)

    _with_retry(operation)


def list_ai_logs(wallet: Optional[str] = None, status: Optional[str] = None, limit: int = 50) -> List[AILog]:
    with session_scope() as session:
        stmt = select(AILog).order_by(AILog.created_at.desc()).limit(limit)
        if wallet:
            stmt = stmt.where(AILog.wallet_address == wallet)
        if status:
            stmt = stmt.where(AILog.status == status)
        return session.execute(stmt).scalars().all()
