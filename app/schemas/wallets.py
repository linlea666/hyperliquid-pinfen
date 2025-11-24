import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")


class WalletImportRequest(BaseModel):
    addresses: List[str] = Field(..., description="Wallet addresses to import.")
    source: str = Field("manual", description="manual|file|api")
    tags: List[str] = Field(default_factory=list)
    batch_size: int = Field(200, ge=1, le=2000)
    dry_run: bool = False
    allow_duplicates: bool = False

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("addresses cannot be empty")
        for addr in value:
            if not ADDRESS_REGEX.match(addr):
                raise ValueError(f"invalid address format: {addr}")
        return value


class WalletImportResult(BaseModel):
    address: str
    status: str
    message: Optional[str] = None
    tags_applied: List[str] = Field(default_factory=list)


class WalletImportResponse(BaseModel):
    requested: int
    imported: int
    skipped: int
    dry_run: bool
    results: List[WalletImportResult]
    source: str
    tags: List[str]
    created_by: Optional[str] = None
    created_at: Optional[str] = None


class WalletSyncRequest(BaseModel):
    address: str = Field(..., description="Wallet address")
    end_time: Optional[int] = Field(None, description="Optional end time ms for incremental fetch")

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str) -> str:
        if not ADDRESS_REGEX.match(value):
            raise ValueError("invalid address format")
        return value


class WalletSyncResponse(BaseModel):
    fills: int
    ledger: int
    positions: int
    orders: int
    portfolio_points: int


class CursorStatusResponse(BaseModel):
    cursors: dict


class LatestRecordsResponse(BaseModel):
    ledger: list
    fills: list
    positions: list
    orders: list


class ScoreResponse(BaseModel):
    score: dict
    metric: dict


class PaginationParams(BaseModel):
    start_time: Optional[int] = Field(None, description="开始时间 ms")
    end_time: Optional[int] = Field(None, description="结束时间 ms")
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


class JobEnqueueResponse(BaseModel):
    job_id: str


class WalletSummary(BaseModel):
    address: str
    status: str
    tags: List[str]
    source: str
    last_synced_at: Optional[str] = None
    created_at: str
    metric: Optional[dict] = None


class WalletListResponse(BaseModel):
    total: int
    items: List[WalletSummary]


class WalletDetailResponse(WalletSummary):
    score: Optional[dict] = None
