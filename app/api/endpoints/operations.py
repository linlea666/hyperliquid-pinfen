import json
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.deps import get_current_user
from app.schemas.notifications import (
    NotificationHistoryResponse,
    NotificationSendRequest,
    SubscriptionCreate,
    SubscriptionResponse,
    TemplateCreate,
    TemplateResponse,
)
from app.schemas.reports import OperationsReport
from app.schemas.tasks import (
    TaskListResponse,
    TaskRecordResponse,
    ProcessingLogListResponse,
    ProcessingLogResponse,
    ProcessingRetryRequest,
    ProcessingRetryResponse,
    ProcessingSummaryResponse,
    ProcessingStageStats,
    AILogListResponse,
    AILogResponse,
)
from app.schemas.schedule import ScheduleCreate, ScheduleResponse
from app.services import notifications as notification_service
from app.services import tasks_service
from app.services import wallets_service
from app.services.notifications import list_history
from app.services import scheduler as scheduler_service
from app.services import processing as processing_service
from app.services import task_queue


router = APIRouter()


@router.get("/tasks", response_model=TaskListResponse, dependencies=[Depends(get_current_user)])
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


@router.get("/ai/logs", response_model=AILogListResponse, dependencies=[Depends(get_current_user)])
def ai_logs(wallet: str | None = None, status: str | None = None, limit: int = Query(50, ge=1, le=200)):
    logs = tasks_service.list_ai_logs(wallet=wallet, status=status, limit=limit)
    return AILogListResponse(
        items=[
            AILogResponse(
                id=log.id,
                wallet_address=log.wallet_address,
                status=log.status,
                provider=log.provider,
                model=log.model,
                prompt=log.prompt,
                response=log.response,
                error=log.error,
                tokens_used=log.tokens_used,
                cost=log.cost,
                created_at=log.created_at.isoformat(),
                finished_at=log.finished_at.isoformat() if log.finished_at else None,
            )
            for log in logs
        ]
    )


@router.get("/processing/logs", response_model=ProcessingLogListResponse, dependencies=[Depends(get_current_user)])
def list_processing_logs(
    wallet: str | None = None,
    stage: str | None = Query(None, pattern="^(sync|score|ai)$"),
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    logs = processing_service.list_logs(address=wallet, stage=stage, status=status, limit=limit)
    return ProcessingLogListResponse(
        items=[
            ProcessingLogResponse(
                id=log.id,
                wallet_address=log.wallet_address,
                stage=log.stage,
                status=log.status,
                attempt=log.attempt,
                scheduled_by=log.scheduled_by,
                payload=log.payload,
                result=log.result,
                error=log.error,
                started_at=log.started_at.isoformat() if log.started_at else None,
                finished_at=log.finished_at.isoformat() if log.finished_at else None,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ]
    )


@router.get("/processing/summary", response_model=ProcessingSummaryResponse, dependencies=[Depends(get_current_user)])
def processing_summary():
    data = processing_service.summary()
    queue = task_queue.get_queue()
    queue_size = queue.count

    def map_log(log):
        return ProcessingLogResponse(
            id=log.id,
            wallet_address=log.wallet_address,
            stage=log.stage,
            status=log.status,
            attempt=log.attempt,
            scheduled_by=log.scheduled_by,
            payload=log.payload,
            result=log.result,
            error=log.error,
            started_at=log.started_at.isoformat() if log.started_at else None,
            finished_at=log.finished_at.isoformat() if log.finished_at else None,
            created_at=log.created_at.isoformat(),
        )

    return ProcessingSummaryResponse(
        stages=[ProcessingStageStats(stage=item["stage"], counts=item["counts"]) for item in data["stages"]],
        pending_rescore=data["pending_rescore"],
        pending_wallets=data["pending_wallets"],
        queue_size=queue_size,
        batch_estimate_seconds=data["batch_estimate_seconds"],
        scope=data["scope"],
        last_failed=[map_log(log) for log in data["failed_logs"]],
        ai_enabled=data.get("ai_enabled", True),
    )


@router.get("/notifications/templates", response_model=List[TemplateResponse], dependencies=[Depends(get_current_user)])
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


@router.post("/notifications/templates", response_model=TemplateResponse, dependencies=[Depends(get_current_user)])
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


@router.post("/notifications/subscriptions", response_model=SubscriptionResponse, dependencies=[Depends(get_current_user)])
def create_subscription(payload: SubscriptionCreate):
    sub = notification_service.subscribe(payload.recipient, payload.template_id, payload.enabled)
    return SubscriptionResponse(id=sub.id, recipient=sub.recipient, template_id=sub.template_id, enabled=bool(sub.enabled))


@router.get("/notifications/subscriptions", response_model=List[SubscriptionResponse], dependencies=[Depends(get_current_user)])
def list_subscriptions(template_id: int | None = None):
    subs = notification_service.list_subscriptions(template_id)
    return [
        SubscriptionResponse(id=sub.id, recipient=sub.recipient, template_id=sub.template_id, enabled=bool(sub.enabled))
        for sub in subs
    ]


@router.post("/notifications/send", response_model=NotificationHistoryResponse, dependencies=[Depends(get_current_user)])
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


@router.get("/notifications/history", response_model=List[NotificationHistoryResponse], dependencies=[Depends(get_current_user)])
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


@router.post("/processing/retry", response_model=ProcessingRetryResponse, dependencies=[Depends(get_current_user)])
def retry_processing(payload: ProcessingRetryRequest):
    stage = payload.stage
    if stage not in {"sync", "score", "ai"}:
        raise HTTPException(status_code=400, detail="invalid stage")
    try:
        if stage == "sync":
            job_id = task_queue.enqueue_wallet_sync(payload.address, scheduled_by="manual", force=True)
        elif stage == "score":
            job_id = task_queue.enqueue_wallet_score(payload.address, scheduled_by="manual", force=True)
            if job_id is None:
                raise HTTPException(status_code=400, detail="score stage already pending or wallet不存在")
        else:
            job_id = task_queue.enqueue_wallet_ai(payload.address, scheduled_by="manual", force=True)
            if job_id is None:
                raise HTTPException(status_code=400, detail="AI stage已在队列或钱包不存在")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ProcessingRetryResponse(stage=stage, job_id=job_id)


@router.get("/reports/operations", response_model=OperationsReport, dependencies=[Depends(get_current_user)])
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
        followed_wallets=overview["followed_wallets"],
        followed_today=overview["followed_today"],
    )


@router.get("/schedules", response_model=List[ScheduleResponse], dependencies=[Depends(get_current_user)])
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


@router.post("/schedules", response_model=ScheduleResponse, dependencies=[Depends(get_current_user)])
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
