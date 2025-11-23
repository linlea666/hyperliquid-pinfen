from typing import List, Optional

from pydantic import BaseModel


class TemplateCreate(BaseModel):
    name: str
    channel: str = "email"
    subject: Optional[str] = None
    content: str
    description: Optional[str] = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    channel: str
    subject: Optional[str]
    content: str
    description: Optional[str]


class SubscriptionCreate(BaseModel):
    recipient: str
    template_id: int
    enabled: bool = True


class SubscriptionResponse(BaseModel):
    id: int
    recipient: str
    template_id: int
    enabled: bool


class NotificationSendRequest(BaseModel):
    template_id: int
    recipient: str
    payload: Optional[dict] = None


class NotificationHistoryResponse(BaseModel):
    id: int
    template_id: int
    recipient: str
    status: str
    attempts: int
    error: Optional[str]
    created_at: str
