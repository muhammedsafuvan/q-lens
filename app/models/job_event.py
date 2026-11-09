import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobEvent(Base):
    __tablename__ = "job_events"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
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
        server_default=text("1"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )

    exception_type: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    exception_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    traceback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    exchange: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    routing_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        CheckConstraint(
            "attempt >= 1",
            name="ck_job_events_attempt_positive",
        ),
        CheckConstraint(
            "event_type IN ('received', 'started', 'succeeded', 'failed', 'retried')",
            name="ck_job_events_event_type",
        ),
        Index(
            "ix_job_events_task_occurred",
            "task_id",
            "occurred_at",
        ),
        Index(
            "ix_job_events_type_occurred",
            "event_type",
            "occurred_at",
        ),
    )
