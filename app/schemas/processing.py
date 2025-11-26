from pydantic import BaseModel, Field


class ProcessingConfigSchema(BaseModel):
    max_parallel_sync: int = Field(gt=0)
    max_parallel_score: int = Field(gt=0)
    retry_limit: int = Field(gt=0)
    retry_delay_seconds: int = Field(ge=0)
    rescore_period_days: int = Field(gt=0)
    rescore_trigger_pct: float = Field(ge=0)
    ai_period_days: int = Field(gt=0)


class ProcessingConfigRequest(BaseModel):
    config: ProcessingConfigSchema


class ProcessingConfigResponse(BaseModel):
    config: ProcessingConfigSchema
