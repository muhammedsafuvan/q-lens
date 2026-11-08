
from contextlib import suppress

import redis
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness check: confirms that the API process is running."""
    return {
        "status": "healthy",
        "service": "queuelens-api",
    }


def _check_postgres() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "healthy"
    except SQLAlchemyError:
        return "unhealthy"


def _check_redis() -> str:
    client = None

    try:
        settings = get_settings()
        client = redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        client.ping()
        return "healthy"
    except RedisError:
        return "unhealthy"
    finally:
        if client is not None:
            with suppress(Exception):
                client.close()


@router.get("/ready")
def readiness_check():
    """Readiness check: verifies the API's required dependencies."""
    dependencies = {
        "postgres": _check_postgres(),
        "redis": _check_redis(),
    }

    is_healthy = all(
        status == "healthy" for status in dependencies.values()
    )

    response = {
        "status": "healthy" if is_healthy else "unhealthy",
        "service": "queuelens-api",
        "dependencies": dependencies,
    }

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content=response,
    )
