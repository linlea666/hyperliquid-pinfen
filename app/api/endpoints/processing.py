from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.processing import ProcessingConfigRequest, ProcessingConfigResponse, ProcessingConfigSchema
from app.services import processing_config

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/processing/config", response_model=ProcessingConfigResponse)
def get_processing_config():
    config = ProcessingConfigSchema(**processing_config.get_processing_config())
    return ProcessingConfigResponse(config=config)


@router.post("/processing/config", response_model=ProcessingConfigResponse)
def update_processing_config(payload: ProcessingConfigRequest):
    try:
        processing_config.save_processing_config(payload.config.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ProcessingConfigResponse(config=payload.config)
