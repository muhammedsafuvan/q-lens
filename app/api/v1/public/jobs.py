from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_workspace
from app.db.session import get_db
from app.repositories.job_events import (
    count_workspace_jobs,
    get_workspace_job_events,
    get_workspace_jobs,
)
from app.schemas.jobs import (
    JobDetail,
    JobEventResponse,
    JobListResponse,
    JobSummary,
)

router = APIRouter(prefix="/jobs", tags=["Public Jobs"])


@router.get("", response_model=JobListResponse)
def list_jobs(
    workspace_id: UUID = Depends(get_current_workspace),
    db: Session = Depends(get_db),
    limit: int = Query(default=10, ge=1, le=100),
):
    jobs = get_workspace_jobs(db, workspace_id, limit)
    total = count_workspace_jobs(db, workspace_id)

    items = [
        JobSummary(
            task_id=job.task_id,
            task_name=job.task_name,
            status=job.event_type,
            occurred_at=job.occurred_at,
            worker_name=job.worker_name,
            queue_name=job.queue_name,
            attempt=job.attempt,
        )
        for job in jobs
    ]

    return JobListResponse(items=items, total=total)


@router.get("/{task_id}", response_model=JobDetail)
def get_job(
    task_id: str,
    workspace_id: UUID = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    events = get_workspace_job_events(db, workspace_id, task_id)

    if not events:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    latest = events[-1]

    return JobDetail(
        task_id=task_id,
        task_name=latest.task_name,
        status=latest.event_type,
        events=[
            JobEventResponse.model_validate(event)
            for event in events
        ],
    )