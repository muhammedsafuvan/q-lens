from fastapi import APIRouter

from app.api.v1.public.events import router as events_router
from app.api.v1.public.jobs import router as jobs_router

router = APIRouter()
router.include_router(events_router)
router.include_router(jobs_router)
