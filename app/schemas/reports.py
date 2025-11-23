from pydantic import BaseModel


class OperationsReport(BaseModel):
    wallet_total: int
    synced_wallets: int
    ledger_events: int
    fills: int
    tasks_running: int
    tasks_failed: int
    notifications_sent: int
    last_sync: str | None
