from typing import Optional, Any

from pydantic import BaseModel, Field


class AIConfigResponse(BaseModel):
    is_enabled: bool
    provider: str
    api_key: Optional[str]
    model: str
    base_url: Optional[str]
    max_tokens: int
    temperature: float
    rate_limit_per_minute: int
    cooldown_minutes: int
    prompt_style: Optional[str]
    prompt_strength: Optional[str]
    prompt_risk: Optional[str]
    prompt_suggestion: Optional[str]
    label_mapping: Optional[str]


class AIConfigUpdateRequest(BaseModel):
    is_enabled: Optional[bool] = None
    provider: Optional[str] = None
    api_key: Optional[str] = Field(default=None, description="使用 *** 表示保持不变")
    model: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    rate_limit_per_minute: Optional[int] = None
    cooldown_minutes: Optional[int] = None
    prompt_style: Optional[str] = None
    prompt_strength: Optional[str] = None
    prompt_risk: Optional[str] = None
    prompt_suggestion: Optional[str] = None
    label_mapping: Optional[str] = None


class AIAnalysisResponse(BaseModel):
    wallet_address: str
    version: str
    score: Optional[float] = None
    style: Optional[str] = None
    strengths: Optional[str] = None
    risks: Optional[str] = None
    suggestion: Optional[str] = None
    follow_ratio: Optional[float] = None
    narrative: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
