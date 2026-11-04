from fastapi import FastAPI

from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Background job observability and reliability intelligence.",
    )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(jobs_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    return app


app = create_app()
