import uuid

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, select
from app.models.job_event import JobEvent as JobEventModel
from app.schemas.events import JobEvent


def insert_job_event(
    db: Session,
    event: JobEvent,
    workspace_id: uuid.UUID,
) -> bool:
    statement = (
        insert(JobEventModel)
        .values(
            **event.model_dump(),
            workspace_id=workspace_id,
        )
        .on_conflict_do_nothing(index_elements=[JobEventModel.event_id])
        .returning(JobEventModel.event_id)
    )

    result = db.execute(statement)
    return result.scalar_one_or_none() is not None


def insert_job_events(
    db: Session,
    events: list[JobEvent],
    workspace_id: uuid.UUID,
) -> int:
    if not events:
        return 0

    values = [
        {
            **event.model_dump(),
            "workspace_id": workspace_id,
        }
        for event in events
    ]

    statement = (
        insert(JobEventModel)
        .values(values)
        .on_conflict_do_nothing(
            index_elements=[JobEventModel.event_id],
        )
        .returning(JobEventModel.event_id)
    )

    result = db.execute(statement)
    return len(result.scalars().all())

def get_workspace_jobs(
    db: Session,
    workspace_id: uuid.UUID,
    limit: int = 10,
) -> list[JobEventModel]:
    ranked = (
        select(
            JobEventModel,
            func.row_number()
            .over(
                partition_by=JobEventModel.task_id,
                order_by=(
                    JobEventModel.occurred_at.desc(),
                    JobEventModel.event_id.desc(),
                ),
            )
            .label("row_num"),
        )
        .where(JobEventModel.workspace_id == workspace_id)
        .subquery()
    )

    latest_event = aliased(JobEventModel, ranked)

    statement = (
        select(latest_event)
        .where(ranked.c.row_num == 1)
        .order_by(ranked.c.occurred_at.desc())
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def count_workspace_jobs(
    db: Session,
    workspace_id: uuid.UUID,
) -> int:
    statement = (
        select(func.count(func.distinct(JobEventModel.task_id)))
        .where(JobEventModel.workspace_id == workspace_id)
    )

    return db.scalar(statement) or 0


def get_workspace_job_events(
    db: Session,
    workspace_id: uuid.UUID,
    task_id: str,
) -> list[JobEventModel]:
    statement = (
        select(JobEventModel)
        .where(
            JobEventModel.workspace_id == workspace_id,
            JobEventModel.task_id == task_id,
        )
        .order_by(
            JobEventModel.occurred_at.asc(),
            JobEventModel.event_id.asc(),
        )
    )

    return list(db.scalars(statement).all())