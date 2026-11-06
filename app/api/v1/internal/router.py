from fastapi import APIRouter

from app.api.v1.internal.events import router as events_router
from app.api.v1.internal.health import router as health_router
from app.api.v1.internal.jobs import router as jobs_router

router = APIRouter()

router.include_router(events_router)
router.include_router(health_router)
router.include_router(jobs_router)