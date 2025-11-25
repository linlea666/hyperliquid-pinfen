from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.schemas.scoring import ScoringConfigResponse, ScoringConfigSchema, ScoringConfigUpdateRequest
from app.services import scoring_config
from app.services import task_queue
from app.core.database import session_scope
from app.models import Wallet

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/scoring/config", response_model=ScoringConfigResponse)
def get_config():
    config = ScoringConfigSchema(**scoring_config.get_scoring_config())
    return ScoringConfigResponse(config=config)


@router.post("/scoring/config", response_model=ScoringConfigResponse)
def update_config(payload: ScoringConfigUpdateRequest):
    config_dict = payload.config.dict()
    try:
        scoring_config.save_scoring_config(config_dict)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    if payload.trigger_rescore:
        # enqueue score jobs for all wallets
        with session_scope() as session:
            wallets = session.query(Wallet.address).all()
        for (address,) in wallets:
            task_queue.enqueue_wallet_score(address, scheduled_by="config")
    return ScoringConfigResponse(config=payload.config)
