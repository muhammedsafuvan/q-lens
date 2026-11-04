import logging
from threading import Event, Thread

from app.workers.event_sender import EventSender

logger = logging.getLogger(__name__)


class EventFlusher:
    """Periodically delivers pending events in the background."""

    def __init__(
        self,
        sender: EventSender,
        interval: float = 5.0,
        max_batches_per_cycle: int = 10,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be greater than 0")

        if max_batches_per_cycle < 1:
            raise ValueError("max_batches_per_cycle must be at least 1")

        self._sender = sender
        self._interval = interval
        self._max_batches_per_cycle = max_batches_per_cycle

        self._stop_event = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start the background flushing thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()

        self._thread = Thread(
            target=self._run,
            name="queuelens-event-flusher",
            daemon=True,
        )
        self._thread.start()

        logger.info("QueueLens event flusher started")

    def stop(self) -> None:
        """Request shutdown and wait for the thread to finish."""
        self._stop_event.set()

        if self._thread is not None and self._thread.is_alive():
            self._thread.join()

        logger.info("QueueLens event flusher stopped")

    def _run(self) -> None:
        try:
            while not self._stop_event.is_set():
                try:
                    batches_sent = 0

                    # Drain a bounded number of batches per cycle.
                    while (
                        not self._stop_event.is_set()
                        and batches_sent < self._max_batches_per_cycle
                    ):
                        acknowledged = self._sender.flush_once()

                        if acknowledged == 0:
                            break

                        batches_sent += 1

                except Exception:
                    logger.exception("Unexpected error in QueueLens event flusher")

                self._stop_event.wait(self._interval)

        finally:
            self._sender.close()
