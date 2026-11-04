import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobEvent(Base):
    __tablename__ = "job_events"

    __table_args__ = (
        CheckConstraint("attempt >= 1", name="ck_job_events_attempt_positive"),
        CheckConstraint(
            "event_type IN ('received', 'started', 'succeeded', 'failed', 'retried')",
            name="ck_job_events_event_type",
        ),
        Index(
            "ix_job_events_task_id_occurred_at",
            "task_id",
            "occurred_at",
        ),
        Index(
            "ix_job_events_event_type_occurred_at",
            "event_type",
            "occurred_at",
        ),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )

    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    task_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    worker_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    queue_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    attempt: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
