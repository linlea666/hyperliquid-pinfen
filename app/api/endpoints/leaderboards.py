import json

from fastapi import APIRouter, Body, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.leaderboard import (
    LeaderboardCreate,
    LeaderboardResponse,
    LeaderboardResultResponse,
    LeaderboardResultEntry,
)
from app.services import leaderboard as lb_service


router = APIRouter()


def serialize_lb(lb) -> LeaderboardResponse:
    return LeaderboardResponse(
        id=lb.id,
        name=lb.name,
        type=lb.type,
        description=lb.description,
        icon=lb.icon,
        style=lb.style,
        accent_color=lb.accent_color,
        badge=lb.badge,
        filters=json.loads(lb.filters) if lb.filters else None,
        sort_key=lb.sort_key,
        sort_order=lb.sort_order,
        period=lb.period,
        is_public=bool(lb.is_public),
    )


@router.get("/leaderboards", response_model=list[LeaderboardResponse])
def list_leaderboards():
    lbs = lb_service.list_leaderboards(public_only=False)
    return [serialize_lb(lb) for lb in lbs]


@router.post("/leaderboards", response_model=LeaderboardResponse, dependencies=[Depends(get_current_user)])
def create_leaderboard(payload: LeaderboardCreate):
    lb = lb_service.create_leaderboard(
        name=payload.name,
        type=payload.type,
        description=payload.description,
        icon=payload.icon,
        style=payload.style,
        accent_color=payload.accent_color,
        badge=payload.badge,
        filters=json.dumps(payload.filters) if payload.filters else None,
        sort_key=payload.sort_key,
        sort_order=payload.sort_order,
        period=payload.period,
        is_public=1 if payload.is_public else 0,
    )
    return serialize_lb(lb)


@router.put("/leaderboards/{lb_id}", response_model=LeaderboardResponse, dependencies=[Depends(get_current_user)])
def update_leaderboard(lb_id: int, payload: LeaderboardCreate):
    lb = lb_service.update_leaderboard(
        lb_id,
        name=payload.name,
        type=payload.type,
        description=payload.description,
        icon=payload.icon,
        style=payload.style,
        accent_color=payload.accent_color,
        badge=payload.badge,
        filters=json.dumps(payload.filters) if payload.filters else None,
        sort_key=payload.sort_key,
        sort_order=payload.sort_order,
        period=payload.period,
        is_public=1 if payload.is_public else 0,
    )
    return serialize_lb(lb)


@router.post("/leaderboards/{lb_id}/run", response_model=LeaderboardResultResponse, dependencies=[Depends(get_current_user)])
def run_leaderboard(lb_id: int):
    try:
        lb_service.run_leaderboard(lb_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return get_leaderboard(lb_id)


@router.post("/leaderboards/run_all", dependencies=[Depends(get_current_user)])
def run_all_leaderboards():
    updated = lb_service.run_all_leaderboards()
    return {"updated": updated}


@router.get("/leaderboards/{lb_id}", response_model=LeaderboardResultResponse)
def get_leaderboard(lb_id: int):
    lbs = lb_service.list_leaderboards(public_only=False)
    lb = next((item for item in lbs if item.id == lb_id), None)
    if not lb:
        raise HTTPException(status_code=404, detail="Leaderboard not found")
    results = lb_service.leaderboard_results(lb_id)
    entries = [
        LeaderboardResultEntry(
            wallet_address=res.wallet_address,
            rank=res.rank,
            score=str(res.score) if res.score is not None else None,
            metrics=json.loads(res.metrics) if res.metrics else None,
        )
        for res in results
    ]
    return LeaderboardResultResponse(leaderboard=serialize_lb(lb), results=entries)
