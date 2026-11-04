# ruff: noqa: B008
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

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
    db: Session = Depends(get_db),
) -> JobEventBatchResponse:
    try:
        connection_info = db.execute(
            text("""
                SELECT
                    current_database(),
                    current_schema(),
                    current_setting('search_path'),
                    inet_server_addr(),
                    inet_server_port(),
                    to_regclass('job_events'),
                    to_regclass('public.job_events')
            """)
        ).fetchone()

        print("QLENS DATABASE DIAGNOSTICS:", connection_info)
        inserted_count = insert_job_events(db, payload.events)
        db.commit()
    except Exception:
        db.rollback()
        raise

    duplicate_count = len(payload.events) - inserted_count

    return JobEventBatchResponse(
        accepted_count=inserted_count,
        duplicate_count=duplicate_count,
    )
