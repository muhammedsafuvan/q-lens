from threading import Event

from app.workers.event_flusher import EventFlusher


class FakeSender:
    def __init__(self, acknowledged: int = 0) -> None:
        self.acknowledged = acknowledged
        self.called = Event()
        self.closed = False
        self.calls = 0
        self.three_calls = Event()

    def flush_once(self) -> int:
        self.calls += 1
        self.called.set()
        if self.calls >= 3:
            self.three_calls.set()
        return self.acknowledged

    def close(self) -> None:
        self.closed = True


def test_flusher_starts_and_stops():
    sender = FakeSender()

    flusher = EventFlusher(
        sender=sender,
        interval=60,
    )

    flusher.start()

    assert sender.called.wait(timeout=2)

    flusher.stop()

    assert sender.closed is True


def test_flusher_drains_multiple_batches():
    sender = FakeSender(acknowledged=100)

    flusher = EventFlusher(
        sender=sender,
        interval=60,
        max_batches_per_cycle=3,
    )

    flusher.start()
    assert sender.three_calls.wait(timeout=2)
    flusher.stop()

    assert sender.calls == 3
    assert sender.closed is True


def test_flusher_rejects_invalid_interval():
    sender = FakeSender()

    try:
        EventFlusher(sender=sender, interval=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass
