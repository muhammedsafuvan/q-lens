from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.health import router as health_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.public.router import router as public_router
from app.api.v1.workspaces.api_keys import router as workspace_api_keys_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Background job observability and reliability intelligence.",
    )

    if settings.session_secret_key:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.session_secret_key,
            session_cookie="qlens_oauth_session",
            max_age=600,
            same_site="lax",
            https_only=settings.app_env == "production",
        )

    app.include_router(health_router)
    app.include_router(public_router, prefix="/api/v1")
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(workspace_api_keys_router, prefix="/api/v1")

    return app


app = create_app()
