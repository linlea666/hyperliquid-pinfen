from fastapi import APIRouter, Body, Depends

from app.api.deps import get_current_user
from app.schemas.ai import AIConfigResponse, AIConfigUpdateRequest
from app.services import ai as ai_service

router = APIRouter()


@router.get("/ai/config", response_model=AIConfigResponse)
def get_config():
    config = ai_service.get_ai_config()
    return AIConfigResponse(
        is_enabled=bool(config.is_enabled),
        provider=config.provider,
        api_key='***' if config.api_key else None,
        model=config.model,
        base_url=config.base_url,
        max_tokens=config.max_tokens,
        temperature=float(config.temperature or 0),
        rate_limit_per_minute=config.rate_limit_per_minute,
        cooldown_minutes=config.cooldown_minutes,
        prompt_style=config.prompt_style,
        prompt_strength=config.prompt_strength,
        prompt_risk=config.prompt_risk,
        prompt_suggestion=config.prompt_suggestion,
    )


@router.post("/ai/config", response_model=AIConfigResponse, dependencies=[Depends(get_current_user)])
def update_config(payload: AIConfigUpdateRequest = Body(...)):
    kwargs = payload.dict(exclude_unset=True)
    if 'api_key' in kwargs and kwargs['api_key'] == '***':
        kwargs.pop('api_key')
    config = ai_service.update_ai_config(**kwargs)
    return AIConfigResponse(
        is_enabled=bool(config.is_enabled),
        provider=config.provider,
        api_key='***' if config.api_key else None,
        model=config.model,
        base_url=config.base_url,
        max_tokens=config.max_tokens,
        temperature=float(config.temperature or 0),
        rate_limit_per_minute=config.rate_limit_per_minute,
        cooldown_minutes=config.cooldown_minutes,
        prompt_style=config.prompt_style,
        prompt_strength=config.prompt_strength,
        prompt_risk=config.prompt_risk,
        prompt_suggestion=config.prompt_suggestion,
    )
