import logging
from typing import Any

from celery import signals

from app.schemas.events import JobEvent, JobEventType
from app.workers.event_buffer import EventBuffer

logger = logging.getLogger(__name__)

event_buffer = EventBuffer(capacity=1000)


def get_pending_events(limit: int = 100) -> list[JobEvent]:
    """Return events currently awaiting delivery."""
    return event_buffer.get_batch(limit)


def _record_event(
    *,
    task_id: str | None,
    task_name: str | None,
    event_type: JobEventType,
    request: Any = None,
) -> None:
    """Create and store an event without affecting task execution."""
    if not task_id or not task_name:
        return

    try:
        delivery_info = getattr(request, "delivery_info", None) or {}

        event = JobEvent(
            task_id=task_id,
            task_name=task_name,
            event_type=event_type,
            worker_name=getattr(request, "hostname", None),
            queue_name=delivery_info.get("queue"),
            attempt=getattr(request, "retries", 0) + 1,
        )

        if not event_buffer.add(event):
            logger.warning(
                "QueueLens event buffer is full. Dropping new event. Total dropped: %s",
                event_buffer.dropped_count,
            )
            return

        logger.info(
            "QueueLens captured job event: %s",
            event.model_dump_json(),
        )
    except Exception:
        # Telemetry must never break application task execution.
        logger.exception("QueueLens failed to capture a job event")


@signals.task_received.connect(
    weak=False,
    dispatch_uid="queuelens_task_received",
)
def on_task_received(request=None, **kwargs: Any) -> None:
    if request is None:
        return

    _record_event(
        task_id=getattr(request, "id", None),
        task_name=getattr(request, "name", None),
        event_type=JobEventType.RECEIVED,
        request=request,
    )


@signals.task_prerun.connect(
    weak=False,
    dispatch_uid="queuelens_task_started",
)
def on_task_started(task_id=None, task=None, **kwargs: Any) -> None:
    if task is None:
        return

    request = task.request

    _record_event(
        task_id=task_id,
        task_name=task.name,
        event_type=JobEventType.STARTED,
        request=request,
    )


@signals.task_success.connect(
    weak=False,
    dispatch_uid="queuelens_task_succeeded",
)
def on_task_succeeded(sender=None, **kwargs: Any) -> None:
    if sender is None:
        return

    request = sender.request

    _record_event(
        task_id=request.id,
        task_name=sender.name,
        event_type=JobEventType.SUCCEEDED,
        request=request,
    )


@signals.task_failure.connect(
    weak=False,
    dispatch_uid="queuelens_task_failed",
)
def on_task_failed(
    sender=None,
    task_id=None,
    **kwargs: Any,
) -> None:
    if sender is None:
        return

    request = sender.request

    _record_event(
        task_id=task_id or request.id,
        task_name=sender.name,
        event_type=JobEventType.FAILED,
        request=request,
    )


@signals.task_retry.connect(
    weak=False,
    dispatch_uid="queuelens_task_retried",
)
def on_task_retried(sender=None, request=None, **kwargs: Any) -> None:
    if sender is None or request is None:
        return

    _record_event(
        task_id=request.id,
        task_name=sender.name,
        event_type=JobEventType.RETRIED,
        request=request,
    )
