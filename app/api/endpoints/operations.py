import json
from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_admin_token
from app.schemas.notifications import (
    NotificationHistoryResponse,
    NotificationSendRequest,
    SubscriptionCreate,
    SubscriptionResponse,
    TemplateCreate,
    TemplateResponse,
)
from app.schemas.reports import OperationsReport
from app.schemas.tasks import TaskListResponse, TaskRecordResponse
from app.schemas.schedule import ScheduleCreate, ScheduleResponse
from app.services import notifications as notification_service
from app.services import tasks_service
from app.services import wallets_service
from app.services.notifications import list_history
from app.services import scheduler as scheduler_service


router = APIRouter()


@router.get("/tasks", response_model=TaskListResponse, dependencies=[Depends(require_admin_token)])
def list_tasks(status: str | None = None, task_type: str | None = None, limit: int = Query(50, ge=1, le=200)):
    items = tasks_service.list_tasks(limit=limit, status=status, task_type=task_type)
    return TaskListResponse(
        items=[
            TaskRecordResponse(
                id=item.id,
                task_type=item.task_type,
                status=item.status,
                payload=item.payload,
                result=item.result,
                error=item.error,
                started_at=item.started_at.isoformat(),
                finished_at=item.finished_at.isoformat() if item.finished_at else None,
            )
            for item in items
        ]
    )


@router.get("/notifications/templates", response_model=List[TemplateResponse], dependencies=[Depends(require_admin_token)])
def list_templates():
    return [
        TemplateResponse(
            id=tpl.id,
            name=tpl.name,
            channel=tpl.channel,
            subject=tpl.subject,
            content=tpl.content,
            description=tpl.description,
        )
        for tpl in notification_service.list_templates()
    ]


@router.post("/notifications/templates", response_model=TemplateResponse, dependencies=[Depends(require_admin_token)])
def create_template(payload: TemplateCreate):
    tpl = notification_service.create_template(payload.name, payload.channel, payload.subject, payload.content, payload.description)
    return TemplateResponse(
        id=tpl.id,
        name=tpl.name,
        channel=tpl.channel,
        subject=tpl.subject,
        content=tpl.content,
        description=tpl.description,
    )


@router.post("/notifications/subscriptions", response_model=SubscriptionResponse, dependencies=[Depends(require_admin_token)])
def create_subscription(payload: SubscriptionCreate):
    sub = notification_service.subscribe(payload.recipient, payload.template_id, payload.enabled)
    return SubscriptionResponse(id=sub.id, recipient=sub.recipient, template_id=sub.template_id, enabled=bool(sub.enabled))


@router.get("/notifications/subscriptions", response_model=List[SubscriptionResponse], dependencies=[Depends(require_admin_token)])
def list_subscriptions(template_id: int | None = None):
    subs = notification_service.list_subscriptions(template_id)
    return [
        SubscriptionResponse(id=sub.id, recipient=sub.recipient, template_id=sub.template_id, enabled=bool(sub.enabled))
        for sub in subs
    ]


@router.post("/notifications/send", response_model=NotificationHistoryResponse, dependencies=[Depends(require_admin_token)])
def send_notification(payload: NotificationSendRequest):
    history = notification_service.send_notification(payload.template_id, payload.recipient, payload.payload)
    return NotificationHistoryResponse(
        id=history.id,
        template_id=history.template_id,
        recipient=history.recipient,
        status=history.status,
        attempts=history.attempts,
        error=history.error,
        created_at=history.created_at.isoformat(),
    )


@router.get("/notifications/history", response_model=List[NotificationHistoryResponse], dependencies=[Depends(require_admin_token)])
def history(limit: int = Query(50, ge=1, le=200)):
    records = list_history(limit)
    return [
        NotificationHistoryResponse(
            id=rec.id,
            template_id=rec.template_id,
            recipient=rec.recipient,
            status=rec.status,
            attempts=rec.attempts,
            error=rec.error,
            created_at=rec.created_at.isoformat(),
        )
        for rec in records
    ]


@router.get("/reports/operations", response_model=OperationsReport)
def operations_report():
    overview = wallets_service.get_wallet_overview()
    task_stats = tasks_service.stats()
    notifications_sent = len(list_history(limit=100))
    return OperationsReport(
        wallet_total=overview["total_wallets"],
        synced_wallets=overview["synced_wallets"],
        ledger_events=overview["ledger_events"],
        fills=overview["fills"],
        tasks_running=task_stats["running"],
        tasks_failed=task_stats["failed"],
        notifications_sent=notifications_sent,
        last_sync=overview["last_sync"],
    )


@router.get("/schedules", response_model=List[ScheduleResponse], dependencies=[Depends(require_admin_token)])
def list_schedules():
    return [
        ScheduleResponse(
            id=job.id,
            name=job.name,
            job_type=job.job_type,
            cron=job.cron,
            payload=json.loads(job.payload) if job.payload else None,
            enabled=bool(job.enabled),
        )
        for job in scheduler_service.list_schedules()
    ]


@router.post("/schedules", response_model=ScheduleResponse, dependencies=[Depends(require_admin_token)])
def create_schedule(payload: ScheduleCreate):
    job = scheduler_service.create_schedule(payload.name, payload.job_type, payload.cron, payload.payload, payload.enabled)
    return ScheduleResponse(
        id=job.id,
        name=job.name,
        job_type=job.job_type,
        cron=job.cron,
        payload=json.loads(job.payload) if job.payload else None,
        enabled=bool(job.enabled),
    )
