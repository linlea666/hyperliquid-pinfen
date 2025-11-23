from typing import List, Optional

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
