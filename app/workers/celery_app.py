
from celery import Celery
from queuelens import QueueLens

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "queuelens",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks.demo"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

queuelens = QueueLens(
    api_key=settings.queuelens_api_key,
    endpoint=settings.ingestion_api_url,
    batch_size=settings.event_batch_size,
    flush_interval=settings.event_flush_interval,
    timeout=settings.event_sender_timeout,
)

queuelens.instrument(celery_app)
