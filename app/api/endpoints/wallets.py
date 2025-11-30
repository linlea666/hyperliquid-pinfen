from fastapi import APIRouter, Body, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.schemas.wallets import (
    WalletImportRequest,
    WalletImportResponse,
    WalletSyncRequest,
    WalletSyncResponse,
    CursorStatusResponse,
    LatestRecordsResponse,
    ScoreResponse,
    PaginationParams,
    JobEnqueueResponse,
    WalletListResponse,
    WalletSummary,
    WalletDetailResponse,
    WalletImportHistoryResponse,
    WalletNoteRequest,
    WalletNoteResponse,
    WalletFollowRequest,
    WalletFollowResponse,
)
from app.services.wallet_importer import import_wallets
from app.services import query as query_service
from app.services import scoring
from app.services import task_queue
from app.services import wallets_service
from app.services import processing as processing_service
from app.schemas.ai import AIAnalysisResponse
from app.services import ai as ai_service

router = APIRouter()


@router.post(
    "/wallets/import",
    response_model=WalletImportResponse,
    summary="Import wallets",
)
def wallets_import(payload: WalletImportRequest = Body(...), user=Depends(get_current_user)) -> WalletImportResponse:
    return import_wallets(payload, created_by=user.email)


@router.get(
    "/wallets/import/history",
    response_model=WalletImportHistoryResponse,
    summary="查看最近导入记录",
)
def wallets_import_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_current_user),
) -> WalletImportHistoryResponse:
    return wallets_service.list_import_records(limit=limit, offset=offset)


@router.post("/wallets/sync", response_model=WalletSyncResponse, summary="Sync wallet data from Hyperliquid")
def wallets_sync(payload: WalletSyncRequest = Body(...)) -> WalletSyncResponse:
    try:
        result = task_queue.run_wallet_sync(payload.address, end_time=payload.end_time, scheduled_by="api")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return WalletSyncResponse(**result)


@router.post(
    "/wallets/sync_async",
    response_model=JobEnqueueResponse,
    summary="后台同步钱包数据（RQ 队列）",
)
def wallets_sync_async(payload: WalletSyncRequest = Body(...)) -> JobEnqueueResponse:
    try:
        job_id = task_queue.enqueue_wallet_sync(payload.address, end_time=payload.end_time, scheduled_by="api")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return JobEnqueueResponse(job_id=job_id)


@router.get("/wallets/status/{address}", response_model=CursorStatusResponse, summary="查看钱包同步游标")
def wallets_status(address: str) -> CursorStatusResponse:
    snapshot = processing_service.get_wallet_snapshot(address)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    return CursorStatusResponse(cursors=query_service.get_cursors(address), **snapshot)


@router.get(
    "/wallets/latest/{address}",
    response_model=LatestRecordsResponse,
    summary="查看钱包最新原始数据（限量）",
)
def wallets_latest(address: str, limit: int = 20) -> LatestRecordsResponse:
    data = query_service.latest_records(address, limit=limit)
    return LatestRecordsResponse(**data)


@router.get("/wallets", response_model=WalletListResponse, summary="钱包列表")
def wallets_list(
    status: str | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    period: str | None = Query(None, description="1d|7d|30d|90d|180d|365d|all"),
    sort_key: str | None = Query(
        None,
        description="win_rate|total_pnl|avg_pnl|volume|trades|max_drawdown",
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return wallets_service.list_wallets(
        limit=limit,
        offset=offset,
        status=status,
        tag=tag,
        search=search,
        period=period,
        sort_key=sort_key,
        sort_order=sort_order,
    )


@router.get("/wallets/following", response_model=WalletListResponse, summary="关注的钱包列表")
def wallets_following(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return wallets_service.list_followed_wallets(limit=limit, offset=offset)


@router.get("/wallets/overview", summary="钱包概览统计")
def wallet_overview():
    return wallets_service.get_wallet_overview()


@router.get("/wallets/{address}", response_model=WalletDetailResponse, summary="钱包详情")
def wallet_detail(address: str) -> WalletDetailResponse:
    data = wallets_service.get_wallet_detail(address)
    if not data:
        raise HTTPException(status_code=404, detail="wallet not found")
    return WalletDetailResponse(**data)


@router.post("/wallets/{address}/note", response_model=WalletNoteResponse, dependencies=[Depends(get_current_user)])
def wallet_update_note(address: str, payload: WalletNoteRequest) -> WalletNoteResponse:
    note = wallets_service.update_wallet_note(address, payload.note)
    if note is None and payload.note is not None:
        raise HTTPException(status_code=404, detail="wallet not found")
    return WalletNoteResponse(address=address, note=note)


@router.post(
    "/wallets/{address}/follow",
    response_model=WalletFollowResponse,
    dependencies=[Depends(get_current_user)],
    summary="关注钱包",
)
def wallet_follow(address: str, payload: WalletFollowRequest | None = Body(None)) -> WalletFollowResponse:
    result = wallets_service.set_wallet_follow(address, True, note=payload.note if payload else None)
    if result is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    return WalletFollowResponse(**result)


@router.delete(
    "/wallets/{address}/follow",
    response_model=WalletFollowResponse,
    dependencies=[Depends(get_current_user)],
    summary="取消关注钱包",
)
def wallet_unfollow(address: str) -> WalletFollowResponse:
    result = wallets_service.set_wallet_follow(address, False)
    if result is None:
        raise HTTPException(status_code=404, detail="wallet not found")
    return WalletFollowResponse(**result)


@router.get("/wallets/{address}/ai", response_model=AIAnalysisResponse, summary="获取钱包 AI 分析")
def wallet_ai_detail(address: str) -> AIAnalysisResponse:
    analysis = ai_service.latest_analysis(address)
    if not analysis:
        raise HTTPException(status_code=404, detail="暂无 AI 分析")
    return AIAnalysisResponse(**ai_service.serialize_analysis(analysis))


@router.post("/wallets/{address}/ai", response_model=AIAnalysisResponse, dependencies=[Depends(get_current_user)], summary="触发 AI 分析")
def wallet_ai_generate(address: str) -> AIAnalysisResponse:
    config = ai_service.get_ai_config()
    if not config.is_enabled:
        raise HTTPException(status_code=400, detail="AI 分析未开启")
    analysis = ai_service.analyze_wallet(address)
    return AIAnalysisResponse(**ai_service.serialize_analysis(analysis))


@router.get("/wallets/ledger", summary="分页查询账本事件")
def wallets_ledger(
    address: str,
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return query_service.paged_events(
        query_service.LedgerEventModel, address, start_time=start_time, end_time=end_time, limit=limit, offset=offset
    )


@router.get("/wallets/fills", summary="分页查询成交")
def wallets_fills(
    address: str,
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return query_service.paged_events(
        query_service.FillModel, address, start_time=start_time, end_time=end_time, limit=limit, offset=offset
    )


@router.get("/wallets/positions", summary="分页查询持仓快照")
def wallets_positions(
    address: str,
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return query_service.paged_events(
        query_service.PositionModel, address, start_time=start_time, end_time=end_time, limit=limit, offset=offset
    )


@router.get("/wallets/orders", summary="分页查询订单历史")
def wallets_orders(
    address: str,
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return query_service.paged_events(
        query_service.OrderModel, address, start_time=start_time, end_time=end_time, limit=limit, offset=offset
    )


def _export_csv(items: list, headers: list):
    def iter_rows():
        yield ",".join(headers) + "\n"
        for row in items:
            yield ",".join([str(row.get(h, "")) for h in headers]) + "\n"

    return iter_rows()


@router.get("/wallets/export/ledger", summary="导出账本事件 CSV")
def export_ledger(address: str, limit: int = Query(1000, ge=1, le=5000)):
    data = query_service.paged_events(query_service.LedgerEventModel, address, limit=limit, offset=0)
    headers = ["time_ms", "delta_type", "amount", "usdc_value", "fee", "token", "vault", "hash"]
    return StreamingResponse(_export_csv(data["items"], headers), media_type="text/csv")


@router.get("/wallets/export/fills", summary="导出成交 CSV")
def export_fills(address: str, limit: int = Query(1000, ge=1, le=5000)):
    data = query_service.paged_events(query_service.FillModel, address, limit=limit, offset=0)
    headers = ["time_ms", "coin", "side", "dir", "px", "sz", "fee", "closed_pnl", "hash"]
    return StreamingResponse(_export_csv(data["items"], headers), media_type="text/csv")


@router.get("/wallets/export/orders", summary="导出订单历史 CSV")
def export_orders(address: str, limit: int = Query(1000, ge=1, le=5000)):
    data = query_service.paged_events(query_service.OrderModel, address, limit=limit, offset=0)
    headers = ["time_ms", "coin", "side", "limit_px", "sz", "order_type", "status", "status_ts", "cloid"]
    return StreamingResponse(_export_csv(data["items"], headers), media_type="text/csv")


@router.get("/wallets/export/positions", summary="导出持仓快照 CSV")
def export_positions(address: str, limit: int = Query(1000, ge=1, le=5000)):
    data = query_service.paged_events(query_service.PositionModel, address, limit=limit, offset=0)
    headers = ["time_ms", "coin", "szi", "entry_px", "pos_value", "unrealized_pnl", "roe", "liq_px", "margin_used"]
    return StreamingResponse(_export_csv(data["items"], headers), media_type="text/csv")


@router.post(
    "/wallets/score",
    response_model=ScoreResponse,
    summary="计算并保存钱包评分/指标",
)
def wallets_score(payload: WalletSyncRequest = Body(...)) -> ScoreResponse:
    metric, score = scoring.compute_metrics(payload.address)
    def serialize(obj):
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        for key, value in list(data.items()):
            if hasattr(value, "isoformat"):
                data[key] = value.isoformat()
            elif isinstance(value, (float, int)) or value is None:
                continue
            else:
                data[key] = str(value)
        return data

    return ScoreResponse(score=serialize(score), metric=serialize(metric))
