from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/health", summary="Health check")
def health_check(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "debug": settings.debug,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
