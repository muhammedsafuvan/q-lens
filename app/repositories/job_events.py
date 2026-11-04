from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.job_event import JobEvent as JobEventModel
from app.schemas.events import JobEvent


def insert_job_event(db: Session, event: JobEvent) -> bool:
    statement = (
        insert(JobEventModel)
        .values(**event.model_dump())
        .on_conflict_do_nothing(
            index_elements=[JobEventModel.event_id],
        )
        .returning(JobEventModel.event_id)
    )

    result = db.execute(statement)
    return result.scalar_one_or_none() is not None


def insert_job_events(db: Session, events: list[JobEvent]) -> int:
    if not events:
        return 0

    statement = (
        insert(JobEventModel)
        .values([event.model_dump() for event in events])
        .on_conflict_do_nothing(
            index_elements=[JobEventModel.event_id],
        )
        .returning(JobEventModel.event_id)
    )

    result = db.execute(statement)
    return len(result.scalars().all())
