from fastapi import APIRouter

from app.api.endpoints import (
    health,
    wallets,
    admin,
    tags,
    leaderboards,
    ai,
    operations,
    auth,
    scoring,
    processing,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["system"])
api_router.include_router(wallets.router, tags=["wallets"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(tags.router, tags=["tags"])
api_router.include_router(leaderboards.router, tags=["leaderboards"])
api_router.include_router(ai.router, tags=["ai"])
api_router.include_router(operations.router, tags=["operations"])
api_router.include_router(scoring.router, tags=["scoring"])
api_router.include_router(processing.router, tags=["processing"])
api_router.include_router(auth.router, tags=["auth"])
