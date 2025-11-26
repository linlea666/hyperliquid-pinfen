from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProcessingConfigSchema(BaseModel):
    max_parallel_sync: int = Field(gt=0)
    max_parallel_score: int = Field(gt=0)
    retry_limit: int = Field(gt=0)
    retry_delay_seconds: int = Field(ge=0)
    rescore_period_days: int = Field(gt=0)
    rescore_trigger_pct: float = Field(ge=0)
    ai_period_days: int = Field(gt=0)
    scope_type: str = Field(default="all")
    scope_recent_days: int = Field(default=7, gt=0)
    scope_tag: str = ""
    batch_size: int = Field(default=50, gt=0)
    batch_interval_seconds: int = Field(default=600, ge=0)
    request_rate_per_min: int = Field(default=120, gt=0)
    sync_cooldown_days: int = Field(default=1, gt=0)
    score_cooldown_days: int = Field(default=7, gt=0)
    ai_cooldown_days: int = Field(default=30, gt=0)


class ProcessingConfigRequest(BaseModel):
    config: ProcessingConfigSchema
    active_template: Optional[str] = None


class ProcessingTemplateSchema(BaseModel):
    key: str
    name: str
    description: str
    overrides: Dict[str, float | int | str]


class ProcessingConfigResponse(BaseModel):
    config: ProcessingConfigSchema
    templates: list[ProcessingTemplateSchema]
    active_template: Optional[str] = None


class ProcessingRunBatchRequest(BaseModel):
    scope_type: Optional[str] = Field(default=None, description="all|today|recent|tag")
    recent_days: Optional[int] = Field(default=None, ge=1)
    tag: Optional[str] = None
    force: bool = False


class ProcessingRunBatchResponse(BaseModel):
    requested: int
    enqueued: int
    skipped: int
