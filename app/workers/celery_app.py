from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "queuelens",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks.demo"],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task tracking
    task_track_started=True,
    result_expires=3600,
    # Broker reliability
    broker_connection_retry_on_startup=True,
)
