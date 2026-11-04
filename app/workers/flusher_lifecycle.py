import logging

from celery import signals

from app.core.config import get_settings
from app.workers.event_flusher import EventFlusher
from app.workers.event_sender import EventSender
from app.workers.instrumentation import event_buffer

logger = logging.getLogger(__name__)

_flusher: EventFlusher | None = None


def start_flusher() -> None:
    global _flusher

    if _flusher is not None:
        return

    settings = get_settings()

    sender = EventSender(
        buffer=event_buffer,
        endpoint=settings.ingestion_api_url,
        batch_size=settings.event_batch_size,
        timeout=settings.event_sender_timeout,
    )

    _flusher = EventFlusher(
        sender=sender,
        interval=settings.event_flush_interval,
    )

    _flusher.start()


def stop_flusher() -> None:
    global _flusher

    if _flusher is None:
        return

    _flusher.stop()
    _flusher = None


@signals.worker_ready.connect(
    weak=False,
    dispatch_uid="queuelens_worker_ready",
)
def on_worker_ready(**kwargs) -> None:
    start_flusher()


@signals.worker_process_init.connect(
    weak=False,
    dispatch_uid="queuelens_worker_process_init",
)
def on_worker_process_init(**kwargs) -> None:
    start_flusher()


@signals.worker_shutdown.connect(
    weak=False,
    dispatch_uid="queuelens_worker_shutdown",
)
def on_worker_shutdown(**kwargs) -> None:
    stop_flusher()


@signals.worker_process_shutdown.connect(
    weak=False,
    dispatch_uid="queuelens_worker_process_shutdown",
)
def on_worker_process_shutdown(**kwargs) -> None:
    stop_flusher()
