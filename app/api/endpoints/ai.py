from fastapi import APIRouter, HTTPException

from app.schemas.ai import AIAnalysisResponse
from app.services import ai as ai_service


router = APIRouter()


@router.post("/wallets/{address}/ai", response_model=AIAnalysisResponse, summary="运行 AI 分析")
def run_ai_analysis(address: str):
    analysis = ai_service.analyze_wallet(address)
    return serialize(analysis)


@router.get("/wallets/{address}/ai", response_model=AIAnalysisResponse, summary="查看最新 AI 分析")
def get_ai_analysis(address: str):
    analysis = ai_service.latest_analysis(address)
    if not analysis:
        raise HTTPException(status_code=404, detail="analysis not found")
    return serialize(analysis)


def serialize(analysis):
    return AIAnalysisResponse(
        wallet_address=analysis.wallet_address,
        version=analysis.version,
        score=float(analysis.score) if analysis.score is not None else None,
        style=analysis.style,
        strengths=analysis.strengths,
        risks=analysis.risks,
        suggestion=analysis.suggestion,
        follow_ratio=float(analysis.follow_ratio) if analysis.follow_ratio is not None else None,
        created_at=analysis.created_at.isoformat(),
    )
