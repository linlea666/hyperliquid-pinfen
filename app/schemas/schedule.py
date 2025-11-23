from typing import Optional

from pydantic import BaseModel, Field


class ScheduleCreate(BaseModel):
    name: str
    job_type: str = Field(..., description="leaderboard_run_all|wallet_sync")
    cron: str
    payload: Optional[dict] = None
    enabled: bool = True


class ScheduleResponse(BaseModel):
    id: int
    name: str
    job_type: str
    cron: str
    payload: Optional[dict]
    enabled: bool
