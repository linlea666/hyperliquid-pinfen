from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.database import Base, engine
import app.models  # noqa: F401
from app.services.scheduler import start_scheduler, stop_scheduler
from app.services.bootstrap import ensure_default_admin, ensure_processing_schema


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.on_event("startup")
    def _startup() -> None:
        Base.metadata.create_all(bind=engine)
        ensure_processing_schema()
        ensure_default_admin()
        start_scheduler()

    @app.on_event("shutdown")
    def _shutdown() -> None:
        stop_scheduler()

    return app


app = create_app()
