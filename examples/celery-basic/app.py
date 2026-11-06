
import os

from celery import Celery
from queuelens import QueueLens

app = Celery(
    "orders",
    broker=os.getenv(
        "CELERY_BROKER_URL",
        "redis://127.0.0.1:6380/0",
    ),
    backend=os.getenv(
        "CELERY_RESULT_BACKEND",
        "redis://127.0.0.1:6380/1",
    ),
)

app.conf.update(
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("tasks",),
)

queuelens = QueueLens()
queuelens.instrument(app)
