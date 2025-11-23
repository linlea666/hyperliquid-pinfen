from typing import List, Optional

from pydantic import BaseModel, Field


class PreferenceResponse(BaseModel):
    default_period: str
    default_sort: str
    theme: str
    favorite_wallets: List[str] = Field(default_factory=list)
    favorite_leaderboards: List[int] = Field(default_factory=list)


class PreferenceUpdate(BaseModel):
    default_period: Optional[str] = None
    default_sort: Optional[str] = None
    theme: Optional[str] = None
    favorite_wallets: Optional[List[str]] = None
    favorite_leaderboards: Optional[List[int]] = None
