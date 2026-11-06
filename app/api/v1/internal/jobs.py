from celery.result import AsyncResult
from fastapi import APIRouter, status

from app.schemas.jobs import DemoJobRequest
from app.workers.celery_app import celery_app
from app.workers.tasks.demo import process_demo_job

router = APIRouter(prefix="/demo/jobs", tags=["Demo Jobs"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def enqueue_demo_job(payload: DemoJobRequest):
    task = process_demo_job.delay(payload.duration_seconds)

    return {
        "message": "Background job accepted",
        "task_id": task.id,
        "status": "PENDING",
    }


@router.get("/{task_id}")
def get_demo_job_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.state,
    }

    if task_result.successful():
        response["result"] = task_result.result

    elif task_result.failed():
        response["error"] = str(task_result.result)

    return response
