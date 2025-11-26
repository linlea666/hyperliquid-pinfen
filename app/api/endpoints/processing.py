from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.processing import (
    ProcessingConfigRequest,
    ProcessingConfigResponse,
    ProcessingConfigSchema,
    ProcessingTemplateSchema,
    ProcessingRunBatchRequest,
    ProcessingRunBatchResponse,
)
from app.services import processing_config, processing
from app.services import task_queue

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/processing/config", response_model=ProcessingConfigResponse)
def get_processing_config():
    bundle = processing_config.get_processing_bundle()
    config = ProcessingConfigSchema(**bundle["config"])
    templates = [ProcessingTemplateSchema(**tpl) for tpl in bundle["templates"]]
    return ProcessingConfigResponse(config=config, templates=templates, active_template=bundle.get("active_template"))


@router.post("/processing/config", response_model=ProcessingConfigResponse)
def update_processing_config(payload: ProcessingConfigRequest):
    try:
        processing_config.save_processing_config(payload.config.dict(), payload.active_template)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    bundle = processing_config.get_processing_bundle()
    config = ProcessingConfigSchema(**bundle["config"])
    templates = [ProcessingTemplateSchema(**tpl) for tpl in bundle["templates"]]
    return ProcessingConfigResponse(config=config, templates=templates, active_template=bundle.get("active_template"))


@router.post("/processing/run_batch", response_model=ProcessingRunBatchResponse)
def run_processing_batch(payload: ProcessingRunBatchRequest):
    config = processing_config.get_processing_config()
    scope_type = payload.scope_type or config.get("scope_type", "all")
    recent_days = payload.recent_days or config.get("scope_recent_days", 7)
    tag = payload.tag if payload.tag is not None else config.get("scope_tag")
    batch_size = config.get("batch_size", 50)
    addresses = processing.select_wallets_for_scope(scope_type, recent_days, tag, batch_size, force=payload.force)
    enqueued = 0
    skipped = 0
    for addr in addresses:
        try:
            task_queue.enqueue_wallet_sync(addr, scheduled_by="batch", force=payload.force)
            enqueued += 1
        except ValueError:
            skipped += 1
    return ProcessingRunBatchResponse(requested=len(addresses), enqueued=enqueued, skipped=skipped)
