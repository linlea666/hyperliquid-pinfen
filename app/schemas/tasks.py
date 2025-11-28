from typing import Dict, List, Optional

from pydantic import BaseModel


class TaskRecordResponse(BaseModel):
    id: int
    task_type: str
    status: str
    payload: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: str
    finished_at: Optional[str] = None


class TaskListResponse(BaseModel):
    items: List[TaskRecordResponse]


class ProcessingLogResponse(BaseModel):
    id: int
    wallet_address: str
    stage: str
    status: str
    attempt: int
    scheduled_by: str
    payload: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    created_at: str


class ProcessingLogListResponse(BaseModel):
    items: List[ProcessingLogResponse]


class ProcessingRetryRequest(BaseModel):
    address: str
    stage: str  # sync | score | ai


class ProcessingRetryResponse(BaseModel):
    stage: str
    job_id: Optional[str] = None


class ProcessingStageStats(BaseModel):
    stage: str
    counts: Dict[str, int]


class ProcessingScopeSummary(BaseModel):
    type: str
    recent_days: Optional[int] = None
    tag: Optional[str] = None
    description: str


class ProcessingSummaryResponse(BaseModel):
    stages: List[ProcessingStageStats]
    pending_rescore: int
    pending_wallets: int
    queue_size: int
    batch_estimate_seconds: int
    scope: ProcessingScopeSummary
    last_failed: List[ProcessingLogResponse]


class AILogResponse(BaseModel):
    id: int
    wallet_address: str
    status: str
    provider: str
    model: str
    prompt: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    tokens_used: int
    cost: Optional[str] = None
    created_at: str
    finished_at: Optional[str] = None


class AILogListResponse(BaseModel):
    items: List[AILogResponse]
