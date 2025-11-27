import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class HyperliquidClient:
    """Lightweight client for Hyperliquid info API."""

    def __init__(self, timeout: Optional[float] = None):
        self.settings = get_settings()
        self.base_url = self.settings.hyperliquid_base_url
        self.timeout = timeout or self.settings.hyperliquid_timeout_sec
        self._client = httpx.Client(timeout=self.timeout)

    def _post(self, payload: Dict[str, Any]) -> Any:
        resp = self._client.post(self.base_url, json=payload, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        return resp.json()

    def user_non_funding_ledger_updates(
        self, user: str, start_time: int, end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {"type": "userNonFundingLedgerUpdates", "user": user, "startTime": start_time}
        if end_time:
            body["endTime"] = end_time
        return self._post(body)

    def user_fills(self, user: str, start_time: int, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """Uses userFillsByTime when start_time specified; otherwise defaults to recent fills."""
        if start_time or end_time:
            body: Dict[str, Any] = {
                "type": "userFillsByTime",
                "user": user,
                "startTime": start_time,
            }
            if end_time:
                body["endTime"] = end_time
            return self._post(body)
        return self._post({"type": "userFills", "user": user})

    def user_funding(self, user: str, start_time: int, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        body: Dict[str, Any] = {"type": "userFunding", "user": user, "startTime": start_time}
        if end_time:
            body["endTime"] = end_time
        return self._post(body)

    def user_fees(self, user: str) -> Dict[str, Any]:
        return self._post({"type": "userFees", "user": user})

    def portfolio(self, user: str) -> Any:
        return self._post({"type": "portfolio", "user": user})

    def historical_orders(self, user: str) -> List[Dict[str, Any]]:
        return self._post({"type": "historicalOrders", "user": user})

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HyperliquidClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
