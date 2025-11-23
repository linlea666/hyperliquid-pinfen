from typing import List, Optional

from pydantic import BaseModel


class OpenOrder(BaseModel):
    coin: str
    limitPx: str
    oid: int
    side: str
    sz: str
    timestamp: int

    class Config:
        extra = "ignore"


class FrontendOpenOrder(OpenOrder):
    isPositionTpsl: bool
    isTrigger: bool
    orderType: str
    origSz: str
    reduceOnly: bool
    triggerCondition: str
    triggerPx: str


class UserFill(BaseModel):
    coin: str
    px: str
    sz: str
    side: str
    time: int
    dir: Optional[str] = None
    closedPnl: Optional[str] = None
    fee: Optional[str] = None
    feeToken: Optional[str] = None
    crossed: Optional[bool] = None
    hash: Optional[str] = None
    oid: Optional[int] = None
    tid: Optional[int] = None
    startPosition: Optional[str] = None
    builderFee: Optional[str] = None

    class Config:
        extra = "ignore"


class HistoricalOrder(BaseModel):
    coin: str
    side: str
    limitPx: str
    sz: str
    oid: int
    timestamp: int
    triggerCondition: str
    isTrigger: bool
    triggerPx: str
    isPositionTpsl: bool
    reduceOnly: bool
    orderType: str
    origSz: str
    tif: str
    cloid: Optional[str] = None

    class Config:
        extra = "ignore"


class HistoricalOrderEnvelope(BaseModel):
    order: HistoricalOrder
    status: str
    statusTimestamp: int


class PortfolioSeriesPoint(BaseModel):
    ts: int
    value: str


class PortfolioInterval(BaseModel):
    accountValueHistory: List[List[str]]
    pnlHistory: List[List[str]]
    vlm: str

    class Config:
        extra = "ignore"


class SubAccountBalance(BaseModel):
    coin: str
    total: str
    hold: str
    entryNtl: str
    token: Optional[int] = None

    class Config:
        extra = "ignore"


class SubAccount(BaseModel):
    name: Optional[str] = None
    subAccountUser: str
    master: str
    assetPositions: Optional[list] = None
    balances: Optional[List[SubAccountBalance]] = None

    class Config:
        extra = "ignore"
