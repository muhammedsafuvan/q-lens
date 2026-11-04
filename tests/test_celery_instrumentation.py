from types import SimpleNamespace
from uuid import uuid4

from app.schemas.events import JobEventType
from app.workers.instrumentation import (
    get_recent_events,
    on_task_started,
)


def test_task_started_signal_creates_event():
    task_id = str(uuid4())

    task = SimpleNamespace(
        name="queuelens.demo.process",
        request=SimpleNamespace(
            id=task_id,
            hostname="worker-1",
            retries=0,
            delivery_info={"queue": "default"},
        ),
    )

    on_task_started(task_id=task_id, task=task)

    events = get_recent_events()
    event = next(event for event in events if event.task_id == task_id)

    assert event.event_type == JobEventType.STARTED
    assert event.task_name == "queuelens.demo.process"
    assert event.worker_name == "worker-1"
    assert event.queue_name == "default"
    assert event.attempt == 1
