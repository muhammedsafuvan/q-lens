from fastapi import FastAPI

from app.api.v1.internal.router import router as internal_router
from app.api.v1.public.router import router as public_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Background job observability and reliability intelligence.",
    )

    app.include_router(public_router, prefix="/api/v1")
    app.include_router(internal_router, prefix="/internal/v1")

    return app


app = create_app()