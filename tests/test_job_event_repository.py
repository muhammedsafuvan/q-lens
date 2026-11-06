
from uuid import uuid4

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.job_event import JobEvent as JobEventModel
from app.models.workspace import Workspace
from app.repositories.job_events import insert_job_event
from app.schemas.events import JobEvent, JobEventType


def test_insert_job_event_is_idempotent():
    event = JobEvent(
        event_id=uuid4(),
        task_id="test-task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.STARTED,
        worker_name="test-worker",
        queue_name="default",
    )

    with SessionLocal() as db:
        try:
            workspace_id = db.scalar(
                select(Workspace.id).where(
                    Workspace.slug == "queuelens-development"
                )
            )

            assert workspace_id is not None, (
                "Development workspace not found. "
                "Run scripts/bootstrap_dev_workspace.py first."
            )

            first_insert = insert_job_event(db, event, workspace_id)
            db.commit()

            second_insert = insert_job_event(db, event, workspace_id)
            db.commit()

            assert first_insert is True
            assert second_insert is False

        finally:
            db.rollback()
            db.execute(
                delete(JobEventModel).where(
                    JobEventModel.event_id == event.event_id
                )
            )
            db.commit()
