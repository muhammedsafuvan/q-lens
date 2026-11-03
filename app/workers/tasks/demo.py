import time

from app.workers.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="queuelens.demo.process",
)
def process_demo_job(self, duration_seconds: int = 3):
    """Simulate a background job."""

    time.sleep(duration_seconds)

    return {
        "task_id": self.request.id,
        "status": "completed",
        "message": "QueueLens background job executed successfully",
        "duration_seconds": duration_seconds,
    }
