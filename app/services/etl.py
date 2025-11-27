import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.database import session_scope
from app.models import (
    FetchCursor,
    Fill,
    LedgerEvent,
    PositionSnapshot,
    OrderHistory,
    PortfolioSeries,
    PortfolioSnapshot,
    Wallet,
)
from app.services.hyperliquid_client import HyperliquidClient
from app.services import local_cache, processing_config
from app.services import local_cache

logger = logging.getLogger(__name__)


def _get_cursor(session, user: str, cursor_type: str) -> int:
    row = session.execute(
        select(FetchCursor).where(FetchCursor.user == user, FetchCursor.cursor_type == cursor_type)
    ).scalar_one_or_none()
    return row.last_time_ms if row else 0


def _upsert_cursor(session, user: str, cursor_type: str, last_time_ms: int) -> None:
    row = session.execute(
        select(FetchCursor).where(FetchCursor.user == user, FetchCursor.cursor_type == cursor_type)
    ).scalar_one_or_none()
    if row:
        session.execute(
            update(FetchCursor)
            .where(FetchCursor.id == row.id)
            .values(last_time_ms=last_time_ms)
        )
    else:
        session.add(FetchCursor(user=user, cursor_type=cursor_type, last_time_ms=last_time_ms))


def _dec(value: Optional[str]):
    return Decimal(value) if value is not None else None


def sync_ledger(user: str, end_time: Optional[int] = None) -> int:
    """Fetch and store ledger updates; returns number of new rows."""
    with session_scope() as session, HyperliquidClient() as client:
        start_time = _get_cursor(session, user, "ledger") + 1
        initial_only = start_time <= 1
        new_rows = 0
        last_time_written: Optional[int] = None
        while True:
            batch = client.user_non_funding_ledger_updates(user=user, start_time=start_time, end_time=end_time)
            if not batch:
                break
            local_cache.append_events(user, "ledger", batch)
            for item in batch:
                delta = item.get("delta", {})
                stmt = sqlite_insert(LedgerEvent).values(
                    user=user,
                    time_ms=item["time"],
                    hash=item.get("hash", ""),
                    delta_type=delta.get("type", ""),
                    vault=delta.get("vault"),
                    token=delta.get("token"),
                    amount=_dec(delta.get("amount") or delta.get("usdc")),
                    usdc_value=_dec(delta.get("usdcValue") or delta.get("usdc")),
                    fee=_dec(delta.get("fee")),
                    native_token_fee=_dec(delta.get("nativeTokenFee")),
                    nonce=delta.get("nonce"),
                    basis=_dec(delta.get("basis")),
                    commission=_dec(delta.get("commission")),
                    closing_cost=_dec(delta.get("closingCost")),
                    net_withdrawn_usd=_dec(delta.get("netWithdrawnUsd")),
                    source_dex=delta.get("sourceDex"),
                    destination_dex=delta.get("destinationDex"),
                    raw_json=json.dumps(item),
                ).prefix_with("OR IGNORE")
                result = session.execute(stmt)
                if result.rowcount:
                    new_rows += 1
                event_time = item["time"]
                start_time = max(start_time, event_time + 1)
                last_time_written = event_time if last_time_written is None else max(last_time_written, event_time)
            if len(batch) < 500:  # reached end
                break
            if initial_only:
                break
        if new_rows:
            cursor_value = last_time_written if last_time_written is not None else (start_time - 1)
            _upsert_cursor(session, user, "ledger", cursor_value)
            local_cache.update_metadata(user, last_ledger_time_ms=cursor_value)
        return new_rows


def sync_fills(user: str, end_time: Optional[int] = None) -> int:
    """Fetch fills with time pagination; returns number of new rows."""
    with session_scope() as session, HyperliquidClient() as client:
        start_time = _get_cursor(session, user, "fills") + 1
        initial_only = start_time <= 1
        new_rows = 0
        last_time_written: Optional[int] = None
        earliest_time: Optional[int] = None
        while True:
            batch = client.user_fills(user=user, start_time=start_time, end_time=end_time)
            if not batch:
                break
            local_cache.append_events(user, "fills", batch)
            for item in batch:
                stmt = sqlite_insert(Fill).values(
                    user=user,
                    time_ms=item["time"],
                    coin=item["coin"],
                    side=item.get("side"),
                    dir=item.get("dir"),
                    px=_dec(item.get("px")),
                    sz=_dec(item.get("sz")),
                    fee=_dec(item.get("fee")),
                    fee_token=item.get("feeToken"),
                    crossed=item.get("crossed"),
                    closed_pnl=_dec(item.get("closedPnl")),
                    start_position=_dec(item.get("startPosition")),
                    hash=item.get("hash"),
                    oid=item.get("oid"),
                    tid=item.get("tid"),
                    builder_fee=_dec(item.get("builderFee")),
                    raw_json=json.dumps(item),
                ).prefix_with("OR IGNORE")
                result = session.execute(stmt)
                if result.rowcount:
                    new_rows += 1
                event_time = item["time"]
                start_time = max(start_time, event_time + 1)
                last_time_written = event_time if last_time_written is None else max(last_time_written, event_time)
                earliest_time = event_time if earliest_time is None else min(earliest_time, event_time)
            if len(batch) < 2000:
                break
            if initial_only:
                break
        if new_rows:
            cursor_value = last_time_written if last_time_written is not None else (start_time - 1)
            _upsert_cursor(session, user, "fills", cursor_value)
            local_cache.update_metadata(user, last_fill_time_ms=cursor_value)
            wallet = session.execute(select(Wallet).where(Wallet.address == user)).scalar_one_or_none()
            computed_ts = earliest_time if earliest_time is not None else cursor_value
            if wallet and computed_ts:
                if wallet.first_trade_time is None or wallet.first_trade_time.timestamp() * 1000 > computed_ts:
                    wallet.first_trade_time = datetime.utcfromtimestamp(computed_ts / 1000)
                    session.add(wallet)
        return new_rows


def sync_funding(user: str, end_time: Optional[int] = None) -> int:
    with session_scope() as session, HyperliquidClient() as client:
        start_time = _get_cursor(session, user, "funding") + 1
        initial_only = start_time <= 1
        new_rows = 0
        last_time_written: Optional[int] = None
        while True:
            batch = client.user_funding(user=user, start_time=start_time, end_time=end_time)
            if not batch:
                break
            local_cache.append_events(user, "funding", batch)
            for item in batch:
                event_time = item["time"]
                start_time = max(start_time, event_time + 1)
                last_time_written = event_time if last_time_written is None else max(last_time_written, event_time)
                new_rows += 1
            if len(batch) < 2000:
                break
            if initial_only:
                break
        if new_rows:
            cursor_value = last_time_written if last_time_written is not None else (start_time - 1)
            _upsert_cursor(session, user, "funding", cursor_value)
            local_cache.update_metadata(user, last_funding_time_ms=cursor_value)
        return new_rows


def sync_user_fees(user: str) -> None:
    with HyperliquidClient() as client:
        payload = client.user_fees(user=user)
    local_cache.write_json(user, "fees.json", payload)
    local_cache.update_metadata(user, last_fee_sync_ms=int(datetime.utcnow().timestamp() * 1000))


def sync_positions(user: str) -> int:
    """Fetch current positions snapshot; returns number of rows written."""
    with session_scope() as session, HyperliquidClient() as client:
        snapshot = client.portfolio(user)
        if not snapshot or not isinstance(snapshot, dict):
            return 0
        asset_positions = snapshot.get("assetPositions", [])
        summary = snapshot.get("marginSummary", {}) or {}
        withdrawable = snapshot.get("withdrawable")
        time_ms = snapshot.get("time")
        written = 0
        for ap in asset_positions:
            pos = ap.get("position", {})
            leverage = pos.get("leverage", {})
            cum_funding = pos.get("cumFunding", {})
            stmt = sqlite_insert(PositionSnapshot).values(
                user=user,
                time_ms=time_ms,
                coin=pos.get("coin"),
                szi=_dec(pos.get("szi")),
                entry_px=_dec(pos.get("entryPx")),
                pos_value=_dec(pos.get("positionValue")),
                unrealized_pnl=_dec(pos.get("unrealizedPnl")),
                roe=_dec(pos.get("returnOnEquity")),
                liq_px=_dec(pos.get("liquidationPx")),
                margin_used=_dec(pos.get("marginUsed")),
                leverage_type=leverage.get("type"),
                leverage_value=_dec(str(leverage.get("value")) if leverage.get("value") is not None else None),
                max_leverage=_dec(str(pos.get("maxLeverage")) if pos.get("maxLeverage") is not None else None),
                cum_funding_all=_dec(cum_funding.get("allTime")),
                cum_funding_open=_dec(cum_funding.get("sinceOpen")),
                cum_funding_change=_dec(cum_funding.get("sinceChange")),
                summary_account_value=_dec(summary.get("accountValue")),
                summary_ntl_pos=_dec(summary.get("totalNtlPos")),
                withdrawable=_dec(withdrawable),
                raw_json=json.dumps(ap),
            ).prefix_with("OR IGNORE")
            result = session.execute(stmt)
            if result.rowcount:
                written += 1
        if written:
            _upsert_cursor(session, user, "positions", time_ms or 0)
        return written


def sync_orders(user: str) -> int:
    """Fetch historical orders (most recent 2000) and store; not paginated by API limit."""
    with session_scope() as session, HyperliquidClient() as client:
        start_time = _get_cursor(session, user, "orders") + 1
        batch = client.historical_orders(user=user)
        new_rows = 0
        for item in batch:
            order = item.get("order", {})
            status = item.get("status")
            status_ts = item.get("statusTimestamp")
            if order.get("timestamp", 0) < start_time:
                continue
            stmt = sqlite_insert(OrderHistory).values(
                user=user,
                time_ms=order.get("timestamp"),
                coin=order.get("coin"),
                side=order.get("side"),
                limit_px=_dec(order.get("limitPx")),
                sz=_dec(order.get("sz")),
                order_type=order.get("orderType"),
                tif=order.get("tif"),
                reduce_only=1 if order.get("reduceOnly") else 0,
                is_trigger=1 if order.get("isTrigger") else 0,
                trigger_px=_dec(order.get("triggerPx")),
                trigger_condition=order.get("triggerCondition"),
                status=status,
                status_ts=status_ts,
                cloid=order.get("cloid"),
                raw_json=json.dumps(item),
            ).prefix_with("OR IGNORE")
            result = session.execute(stmt)
            if result.rowcount:
                new_rows += 1
            start_time = max(start_time, order.get("timestamp", 0) + 1)
        if new_rows:
            _upsert_cursor(session, user, "orders", start_time - 1)
        return new_rows


def _should_refresh_portfolio(session, user: str) -> bool:
    now = datetime.utcnow()
    min_hours = processing_config.get_processing_config().get("portfolio_refresh_hours", 24)
    last = session.execute(
        select(PortfolioSnapshot.updated_at).where(PortfolioSnapshot.user == user).order_by(PortfolioSnapshot.updated_at.desc())
    ).scalars().first()
    if not last:
        return True
    return (now - last).total_seconds() >= min_hours * 3600


def sync_portfolio_series(user: str, force: bool = False) -> int:
    """Fetch portfolio time series and store account value/pnl per interval."""
    with session_scope() as session:
        if not force and not _should_refresh_portfolio(session, user):
            return 0
        with HyperliquidClient() as client:
            data = client.portfolio(user=user)
        if not data or not isinstance(data, list):
            return 0
        written = 0
        for interval_pair in data:
            if not isinstance(interval_pair, list) or len(interval_pair) != 2:
                continue
            interval, payload = interval_pair
            av_hist = {int(ts): val for ts, val in payload.get("accountValueHistory", [])}
            pnl_hist = {int(ts): val for ts, val in payload.get("pnlHistory", [])}
            ts_set = set(av_hist.keys()) | set(pnl_hist.keys())
            for ts in ts_set:
                stmt = sqlite_insert(PortfolioSeries).values(
                    user=user,
                    interval=interval,
                    ts=ts,
                    account_value=_dec(av_hist.get(ts)),
                    pnl=_dec(pnl_hist.get(ts)),
                    vlm=_dec(payload.get("vlm")),
                ).prefix_with("OR IGNORE")
                result = session.execute(stmt)
                if result.rowcount:
                    written += 1
            ret_pct, drawdown_pct = _compute_portfolio_metrics(list(av_hist.items()))
            snapshot_stmt = sqlite_insert(PortfolioSnapshot).values(
                user=user,
                period=interval,
                payload=json.dumps(payload),
                return_pct=ret_pct,
                max_drawdown_pct=drawdown_pct,
                volume=_dec(payload.get("vlm")),
                updated_at=datetime.utcnow(),
            ).prefix_with("OR REPLACE")
            session.execute(snapshot_stmt)
        return written


def _compute_portfolio_metrics(av_hist: list[tuple[int, str]]) -> tuple[Optional[Decimal], Optional[Decimal]]:
    if not av_hist:
        return None, None
    sorted_hist = sorted(av_hist, key=lambda x: x[0])
    values: List[Decimal] = []
    for _, val in sorted_hist:
        try:
            values.append(Decimal(str(val)))
        except Exception:
            continue
    if len(values) < 2:
        return None, None
    start_val = values[0]
    end_val = values[-1]
    if start_val == 0:
        ret_pct = None
    else:
        ret_pct = (end_val - start_val) / start_val
    peak = values[0]
    max_drawdown = Decimal("0")
    for val in values:
        if val > peak:
            peak = val
        drawdown = (val - peak) / peak if peak != 0 else Decimal("0")
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return ret_pct, max_drawdown
