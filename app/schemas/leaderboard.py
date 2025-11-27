from typing import List, Optional

from pydantic import BaseModel, Field


class LeaderboardCreate(BaseModel):
    name: str
    type: str = "custom"
    description: Optional[str] = None
    icon: Optional[str] = None
    style: str = "table"
    accent_color: str = "#7c3aed"
    badge: Optional[str] = None
    filters: Optional[dict] = None
    sort_key: str = "total_pnl"
    sort_order: str = "desc"
    period: str = "all"
    is_public: bool = True
    result_limit: int = Field(20, ge=1, le=200)
    auto_refresh_minutes: int = Field(0, ge=0, le=24 * 60)


class LeaderboardResponse(BaseModel):
    id: int
    name: str
    type: str
    description: Optional[str]
    icon: Optional[str]
    style: str
    accent_color: str
    badge: Optional[str]
    filters: Optional[dict]
    sort_key: str
    sort_order: str
    period: str
    is_public: bool
    result_limit: int
    auto_refresh_minutes: int


class LeaderboardResultEntry(BaseModel):
    wallet_address: str
    rank: int
    score: Optional[str]
    metrics: Optional[dict]


class LeaderboardResultResponse(BaseModel):
    leaderboard: LeaderboardResponse
    results: List[LeaderboardResultEntry]
