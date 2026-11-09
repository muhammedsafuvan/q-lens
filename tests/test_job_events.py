import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.events import JobEvent, JobEventType


def test_job_event_generates_default_values():
    event = JobEvent(
        task_id="task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.STARTED,
    )

    assert isinstance(event.event_id, uuid.UUID)
    assert event.attempt == 1
    assert event.occurred_at.tzinfo is not None


def test_job_event_accepts_explicit_values():
    occurred_at = datetime.now(UTC)

    event = JobEvent(
        task_id="task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.FAILED,
        occurred_at=occurred_at,
        worker_name="worker-1",
        queue_name="default",
        attempt=2,
    )

    assert event.event_type == JobEventType.FAILED
    assert event.attempt == 2
    assert event.worker_name == "worker-1"


def test_job_event_rejects_invalid_attempt():
    with pytest.raises(ValidationError):
        JobEvent(
            task_id="task-123",
            task_name="queuelens.demo.process",
            event_type=JobEventType.STARTED,
            attempt=0,
        )


def test_job_event_rejects_naive_datetime():
    with pytest.raises(ValidationError):
        JobEvent(
            task_id="task-123",
            task_name="queuelens.demo.process",
            event_type=JobEventType.STARTED,
            occurred_at=datetime(2026, 11, 4, 10, 0, 0),
        )


def test_job_event_accepts_diagnostic_metadata():
    event = JobEvent(
        task_id="task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.FAILED,
        attempt=2,
        exception_type="ValueError",
        exception_message="Invalid order",
        traceback="Traceback (most recent call last): ...",
        exchange="orders",
        routing_key="orders.process",
    )

    assert event.exception_type == "ValueError"
    assert event.exception_message == "Invalid order"
    assert event.traceback.startswith("Traceback")
    assert event.exchange == "orders"
    assert event.routing_key == "orders.process"
