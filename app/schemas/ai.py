from typing import Optional

from pydantic import BaseModel


class AIAnalysisResponse(BaseModel):
    wallet_address: str
    version: str
    score: Optional[float]
    style: Optional[str]
    strengths: Optional[str]
    risks: Optional[str]
    suggestion: Optional[str]
    follow_ratio: Optional[float]
    created_at: str
