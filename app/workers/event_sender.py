import logging

import httpx
from pydantic import ValidationError

from app.schemas.events import JobEventBatchResponse
from app.workers.event_buffer import EventBuffer

logger = logging.getLogger(__name__)


class EventSender:
    """Deliver buffered events to the QueueLens ingestion API."""

    def __init__(
        self,
        buffer: EventBuffer,
        endpoint: str,
        batch_size: int = 100,
        timeout: float = 5.0,
        client: httpx.Client | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")

        self._buffer = buffer
        self._endpoint = endpoint
        self._batch_size = batch_size
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None

    def flush_once(self) -> int | None:
        """
        Send one batch of events.

        Events are acknowledged only after the API confirms that
        every event was either accepted or recognized as a duplicate.

        Returns the number of events acknowledged.
        """
        logger.info(
            "QueueLens flush triggered. Pending events: %s",
            len(self._buffer),
        )
        events = self._buffer.get_batch(limit=self._batch_size)

        if not events:
            return 0

        payload = {"events": [event.model_dump(mode="json") for event in events]}

        try:
            response = self._client.post(
                self._endpoint,
                json=payload,
            )
            response.raise_for_status()

            result = JobEventBatchResponse.model_validate(response.json())

            processed_count = result.accepted_count + result.duplicate_count

            if (
                result.accepted_count < 0
                or result.duplicate_count < 0
                or processed_count != len(events)
            ):
                raise ValueError("Ingestion API returned inconsistent batch counts")

        except (
            httpx.HTTPError,
            ValidationError,
            ValueError,
        ):
            logger.exception(
                "QueueLens failed to deliver event batch. "
                "Retaining %s events for retry.",
                len(events),
            )
            return None

        acknowledged_count = self._buffer.acknowledge(
            {event.event_id for event in events}
        )

        logger.info(
            "QueueLens delivered event batch: "
            "accepted=%s duplicates=%s acknowledged=%s",
            result.accepted_count,
            result.duplicate_count,
            acknowledged_count,
        )

        return acknowledged_count

    def close(self) -> None:
        """Close the HTTP client if this sender owns it."""
        if self._owns_client:
            self._client.close()
