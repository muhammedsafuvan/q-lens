import uuid

import pytest

from app.schemas.events import JobEvent, JobEventType
from app.workers.event_buffer import EventBuffer


def create_event() -> JobEvent:
    return JobEvent(
        event_id=uuid.uuid4(),
        task_id="task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.STARTED,
    )


def test_add_event():
    buffer = EventBuffer(capacity=10)
    event = create_event()

    assert buffer.add(event) is True
    assert len(buffer) == 1


def test_get_batch_does_not_remove_events():
    buffer = EventBuffer(capacity=10)
    event = create_event()

    buffer.add(event)

    assert buffer.get_batch() == [event]
    assert buffer.get_batch() == [event]
    assert len(buffer) == 1


def test_buffer_rejects_new_events_when_full():
    buffer = EventBuffer(capacity=1)

    first_event = create_event()
    second_event = create_event()

    assert buffer.add(first_event) is True
    assert buffer.add(second_event) is False

    assert buffer.get_batch() == [first_event]
    assert buffer.dropped_count == 1


def test_acknowledge_removes_only_matching_events():
    buffer = EventBuffer(capacity=10)

    first_event = create_event()
    second_event = create_event()
    third_event = create_event()

    buffer.add(first_event)
    buffer.add(second_event)
    buffer.add(third_event)

    removed_count = buffer.acknowledge({second_event.event_id})

    assert removed_count == 1
    assert buffer.get_batch() == [first_event, third_event]


def test_acknowledge_returns_zero_for_unknown_ids():
    buffer = EventBuffer()
    event = create_event()

    buffer.add(event)

    removed_count = buffer.acknowledge({uuid.uuid4()})

    assert removed_count == 0
    assert len(buffer) == 1


def test_get_batch_rejects_invalid_limit():
    buffer = EventBuffer()

    with pytest.raises(ValueError):
        buffer.get_batch(limit=0)


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        EventBuffer(capacity=0)
