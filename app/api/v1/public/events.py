# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.security import get_current_workspace
from app.db.session import get_db
from app.repositories.job_events import insert_job_events
from app.schemas.events import JobEventBatch, JobEventBatchResponse

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "/batch",
    response_model=JobEventBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_events(
    payload: JobEventBatch,
    workspace_id: UUID = Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> JobEventBatchResponse:
    try:
        inserted_count = insert_job_events(
            db,
            payload.events,
            workspace_id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    duplicate_count = len(payload.events) - inserted_count

    return JobEventBatchResponse(
        accepted_count=inserted_count,
        duplicate_count=duplicate_count,
    )
