from threading import Event

from app.workers.event_flusher import EventFlusher


class FakeSender:
    def __init__(self, acknowledged: int = 0) -> None:
        self.acknowledged = acknowledged
        self.called = Event()
        self.closed = False
        self.calls = 0
        self.three_calls = Event()

    def flush_once(self) -> int | None:
        self.calls += 1
        self.called.set()
        if self.calls == 3:
            self.three_calls.set()
        return self.acknowledged  if self.calls <= 3 else 0

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

    assert sender.calls == 4
    assert sender.closed is True


def test_flusher_rejects_invalid_interval():
    sender = FakeSender()

    try:
        EventFlusher(sender=sender, interval=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass



def test_flusher_flushes_pending_events_on_shutdown():
    class ShutdownFakeSender:
        def __init__(self):
            self.calls = 0
            self.first_call = Event()
            self.acknowledged = 0
            self.closed = False

        def flush_once(self):
            self.calls += 1

            if self.calls == 1:
                # Normal periodic cycle finds nothing.
                self.first_call.set()
                return 0

            # Simulate pending events becoming available
            # before the shutdown flush.
            self.acknowledged += 2
            return 2

        def close(self):
            self.closed = True

    sender = ShutdownFakeSender()

    flusher = EventFlusher(
        sender=sender,
        interval=60,
    )

    flusher.start()

    assert sender.first_call.wait(timeout=2)

    flusher.stop()

    assert sender.calls == 2
    assert sender.acknowledged == 2
    assert sender.closed is True

def test_backoff_increases_exponentially():
    sender = FakeSender()

    flusher = EventFlusher(
        sender=sender,
        base_backoff=1,
        max_backoff=30,
    )

    backoff = 1

    expected = [2, 4, 8, 16, 30, 30]

    for value in expected:
        backoff = flusher._increase_backoff(backoff)
        assert backoff == value


def test_backoff_respects_custom_maximum():
    sender = FakeSender()

    flusher = EventFlusher(
        sender=sender,
        base_backoff=2,
        max_backoff=8,
    )

    backoff = 2

    for expected in [4, 8, 8, 8]:
        backoff = flusher._increase_backoff(backoff)
        assert backoff == expected


def test_retry_delay_uses_equal_jitter(monkeypatch):
    sender = FakeSender()

    flusher = EventFlusher(
        sender=sender,
        base_backoff=4,
        max_backoff=30,
    )

    captured = {}

    def fake_uniform(lower, upper):
        captured["lower"] = lower
        captured["upper"] = upper
        return lower

    monkeypatch.setattr(
        "app.workers.event_flusher.random.uniform",
        fake_uniform,
    )

    delay = flusher._calculate_retry_delay(4)

    assert captured["lower"] == 2
    assert captured["upper"] == 4
    assert delay == 2


def test_backoff_rejects_invalid_configuration():
    sender = FakeSender()

    try:
        EventFlusher(sender=sender, base_backoff=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    try:
        EventFlusher(
            sender=sender,
            base_backoff=5,
            max_backoff=2,
        )
        assert False, "Expected ValueError"
    except ValueError:
        pass