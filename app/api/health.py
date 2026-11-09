from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "queuelens-api",
    }


@router.get("/ready")
def readiness_check():
    try:
        with engine.connect():
            pass
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "service": "queuelens-api",
                "dependencies": {
                    "postgres": "unhealthy",
                },
            },
        ) from exc

    return {
        "status": "healthy",
        "service": "queuelens-api",
        "dependencies": {
            "postgres": "healthy",
        },
    }
