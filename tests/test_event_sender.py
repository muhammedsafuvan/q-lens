import uuid

import httpx

from app.schemas.events import JobEvent, JobEventType
from app.workers.event_buffer import EventBuffer
from app.workers.event_sender import EventSender

ENDPOINT = "http://testserver/api/v1/events/batch"


def create_event() -> JobEvent:
    return JobEvent(
        event_id=uuid.uuid4(),
        task_id="task-123",
        task_name="queuelens.demo.process",
        event_type=JobEventType.STARTED,
    )


def create_sender(
    buffer: EventBuffer,
    handler,
) -> EventSender:
    client = httpx.Client(transport=httpx.MockTransport(handler))

    return EventSender(
        buffer=buffer,
        endpoint=ENDPOINT,
        batch_size=100,
        client=client,
    )


def test_flush_successfully_acknowledges_events():
    buffer = EventBuffer()
    event = create_event()
    buffer.add(event)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == ENDPOINT

        payload = __import__("json").loads(request.content)
        assert len(payload["events"]) == 1

        return httpx.Response(
            202,
            json={
                "accepted_count": 1,
                "duplicate_count": 0,
            },
        )

    sender = create_sender(buffer, handler)

    assert sender.flush_once() == 1
    assert len(buffer) == 0

    sender.close()


def test_flush_acknowledges_duplicate_events():
    buffer = EventBuffer()
    event = create_event()
    buffer.add(event)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "accepted_count": 0,
                "duplicate_count": 1,
            },
        )

    sender = create_sender(buffer, handler)

    assert sender.flush_once() == 1
    assert len(buffer) == 0

    sender.close()


def test_failed_request_retains_events():
    buffer = EventBuffer()
    event = create_event()
    buffer.add(event)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    sender = create_sender(buffer, handler)

    assert sender.flush_once() == 0
    assert len(buffer) == 1

    sender.close()


def test_invalid_response_retains_events():
    buffer = EventBuffer()
    event = create_event()
    buffer.add(event)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            202,
            json={
                "accepted_count": 0,
                "duplicate_count": 0,
            },
        )

    sender = create_sender(buffer, handler)

    assert sender.flush_once() == 0
    assert len(buffer) == 1

    sender.close()


def test_empty_buffer_does_not_send_request():
    buffer = EventBuffer()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Unexpected HTTP request")

    sender = create_sender(buffer, handler)

    assert sender.flush_once() == 0
    assert len(buffer) == 0

    sender.close()
