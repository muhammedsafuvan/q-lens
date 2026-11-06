
import multiprocessing
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from celery import Celery, signals
from queuelens.config import QueueLensConfig
from queuelens.instrumentation.celery import CeleryInstrumentation


@pytest.fixture
def instrumentation():
    config = QueueLensConfig(
        api_key="test-key",
        endpoint="http://localhost:8001/internal/v1/events/batch",
    )

    instance = CeleryInstrumentation(config)
    instance._celery_app = SimpleNamespace()

    return instance

def _run_flusher_initialization_in_child(
    instrumentation,
    parent_flusher,
    connection,
):
    try:
        with (
            patch(
                "queuelens.instrumentation.celery.EventSender",
                return_value=MagicMock(),
            ),
            patch(
                "queuelens.instrumentation.celery.EventFlusher",
            ) as flusher_factory,
        ):
            child_flusher = MagicMock()
            child_flusher.is_alive = True
            child_flusher.stop.return_value = True
            flusher_factory.return_value = child_flusher

            instrumentation._on_worker_process_init()

            connection.send(
                {
                    "pid": os.getpid(),
                    "flusher_pid": instrumentation._flusher_pid,
                    "new_flusher_created": (
                        instrumentation._flusher is not parent_flusher
                    ),
                    "flusher_started": child_flusher.start.called,
                }
            )

            instrumentation._on_worker_process_shutdown()

    finally:
        connection.close()

def test_task_received_handles_metadata_exception(instrumentation):
    class BrokenRequest:
        task = SimpleNamespace(app=instrumentation._celery_app)

        @property
        def id(self):
            raise RuntimeError("metadata unavailable")

    instrumentation._on_task_received(request=BrokenRequest())

    assert len(instrumentation._buffer) == 0


def test_task_started_handles_metadata_exception(instrumentation):
    class BrokenTask:
        app = instrumentation._celery_app

        @property
        def name(self):
            raise RuntimeError("metadata unavailable")

    instrumentation._on_task_started(
        task_id="task-123",
        task=BrokenTask(),
    )

    assert len(instrumentation._buffer) == 0


def test_task_succeeded_handles_metadata_exception(instrumentation):
    class BrokenSender:
        app = instrumentation._celery_app

        @property
        def request(self):
            raise RuntimeError("request unavailable")

    instrumentation._on_task_succeeded(sender=BrokenSender())

    assert len(instrumentation._buffer) == 0


def test_task_failed_handles_metadata_exception(instrumentation):
    class BrokenSender:
        app = instrumentation._celery_app

        @property
        def request(self):
            raise RuntimeError("request unavailable")

    instrumentation._on_task_failed(sender=BrokenSender())

    assert len(instrumentation._buffer) == 0


def test_task_retried_handles_metadata_exception(instrumentation):
    class BrokenRequest:
        @property
        def id(self):
            raise RuntimeError("metadata unavailable")

    sender = SimpleNamespace(
        name="orders.process",
        app=instrumentation._celery_app,
    )

    instrumentation._on_task_retried(
        sender=sender,
        request=BrokenRequest(),
    )

    assert len(instrumentation._buffer) == 0


def test_buffer_failure_does_not_escape_signal_handler(instrumentation):
    request = SimpleNamespace(
        id="task-123",
        name="orders.process",
        task=SimpleNamespace(app=instrumentation._celery_app),
        delivery_info={},
        hostname="worker-1",
        retries=0,
    )

    with patch.object(
        instrumentation._buffer,
        "add",
        side_effect=RuntimeError("buffer unavailable"),
    ):
        instrumentation._on_task_received(request=request)

    assert len(instrumentation._buffer) == 0


def test_task_received_ignores_another_celery_app(instrumentation):
    another_app = SimpleNamespace()

    request = SimpleNamespace(
        id="task-123",
        name="orders.process",
        task=SimpleNamespace(app=another_app),
        delivery_info={},
        hostname="worker-1",
        retries=0,
    )

    instrumentation._on_task_received(request=request)

    assert len(instrumentation._buffer) == 0


def test_task_received_accepts_its_own_celery_app(instrumentation):
    request = SimpleNamespace(
        id="task-123",
        name="orders.process",
        task=SimpleNamespace(app=instrumentation._celery_app),
        delivery_info={},
        hostname="worker-1",
        retries=0,
    )

    instrumentation._on_task_received(request=request)

    assert len(instrumentation._buffer) == 1


def test_sender_initialization_failure_is_non_fatal(instrumentation):
    with patch(
        "queuelens.instrumentation.celery.EventSender",
        side_effect=RuntimeError("sender unavailable"),
    ):
        instrumentation._on_worker_ready()

    assert instrumentation._flusher is None


def test_flusher_initialization_failure_closes_sender(instrumentation):
    sender = MagicMock()

    with (
        patch(
            "queuelens.instrumentation.celery.EventSender",
            return_value=sender,
        ),
        patch(
            "queuelens.instrumentation.celery.EventFlusher",
            side_effect=RuntimeError("flusher unavailable"),
        ),
    ):
        instrumentation._on_worker_ready()

    sender.close.assert_called_once()
    assert instrumentation._flusher is None


def test_flusher_start_failure_closes_sender(instrumentation):
    sender = MagicMock()
    flusher = MagicMock()
    flusher.start.side_effect = RuntimeError("thread unavailable")

    with (
        patch(
            "queuelens.instrumentation.celery.EventSender",
            return_value=sender,
        ),
        patch(
            "queuelens.instrumentation.celery.EventFlusher",
            return_value=flusher,
        ),
    ):
        instrumentation._on_worker_ready()

    sender.close.assert_called_once()
    assert instrumentation._flusher is None


def test_flusher_shutdown_failure_is_non_fatal(instrumentation):
    flusher = MagicMock()
    flusher.stop.side_effect = RuntimeError("shutdown failure")

    instrumentation._flusher = flusher
    instrumentation._flusher_pid = os.getpid()

    instrumentation._on_worker_shutdown()

    flusher.stop.assert_called_once()
    assert instrumentation._flusher is flusher
    assert instrumentation._flusher_pid == os.getpid()


def test_flusher_initialization_can_retry(instrumentation):
    flusher = MagicMock()

    with (
        patch(
            "queuelens.instrumentation.celery.EventSender",
            side_effect=[
                RuntimeError("temporary failure"),
                MagicMock(),
            ],
        ),
        patch(
            "queuelens.instrumentation.celery.EventFlusher",
            return_value=flusher,
        ),
    ):
        instrumentation._start_flusher()
        assert instrumentation._flusher is None

        instrumentation._start_flusher()
        assert instrumentation._flusher is flusher

    flusher.start.assert_called_once()

def test_multiple_celery_apps_do_not_capture_each_others_tasks(
    instrumentation,
):
    app_one = Celery("app_one")
    app_two = Celery("app_two")

    @app_one.task(name="app_one.process")
    def app_one_task():
        pass

    @app_two.task(name="app_two.process")
    def app_two_task():
        pass

    instrumentation_two = CeleryInstrumentation(instrumentation._config)

    instrumentation.instrument(app_one)
    instrumentation_two.instrument(app_two)

    try:
        # Dispatch a task from app one.
        app_one_task.push_request(id="task-one")

        try:
            signals.task_prerun.send(
                sender=app_one_task,
                task_id="task-one",
                task=app_one_task,
            )
        finally:
            app_one_task.pop_request()

        assert len(instrumentation._buffer) == 1
        assert len(instrumentation_two._buffer) == 0

        # Dispatch a task from app two.
        app_two_task.push_request(id="task-two")

        try:
            signals.task_prerun.send(
                sender=app_two_task,
                task_id="task-two",
                task=app_two_task,
            )
        finally:
            app_two_task.pop_request()

        assert len(instrumentation._buffer) == 1
        assert len(instrumentation_two._buffer) == 1

    finally:
        instrumentation.close()
        instrumentation_two.close()

def test_worker_process_init_creates_new_flusher_after_fork(
    instrumentation,
):
    parent_flusher = MagicMock()
    parent_flusher.is_alive = True

    child_flusher = MagicMock()
    child_flusher.is_alive = True

    parent_sender = MagicMock()
    child_sender = MagicMock()

    with (
        patch(
            "queuelens.instrumentation.celery.os.getpid",
            side_effect=[100, 200],
        ),
        patch(
            "queuelens.instrumentation.celery.EventSender",
            side_effect=[parent_sender, child_sender],
        ),
        patch(
            "queuelens.instrumentation.celery.EventFlusher",
            side_effect=[parent_flusher, child_flusher],
        ) as flusher_factory,
    ):
        # Simulate initialization in the parent process.
        instrumentation._on_worker_ready()

        assert instrumentation._flusher is parent_flusher
        assert instrumentation._flusher_pid == 100

        # Simulate initialization in a forked child process.
        instrumentation._on_worker_process_init()

        assert instrumentation._flusher is child_flusher
        assert instrumentation._flusher_pid == 200

        assert flusher_factory.call_count == 2

        # The child must not attempt to stop the parent's flusher.
        parent_flusher.stop.assert_not_called()


def test_worker_process_init_does_not_create_duplicate_flusher(
    instrumentation,
):
    flusher = MagicMock()
    flusher.is_alive = True

    with (
        patch(
            "queuelens.instrumentation.celery.os.getpid",
            return_value=100,
        ),
        patch(
            "queuelens.instrumentation.celery.EventSender",
        ) as sender_factory,
        patch(
            "queuelens.instrumentation.celery.EventFlusher",
            return_value=flusher,
        ) as flusher_factory,
    ):
        instrumentation._on_worker_ready()
        instrumentation._on_worker_process_init()

        assert instrumentation._flusher is flusher
        assert instrumentation._flusher_pid == 100

        sender_factory.assert_called_once()
        flusher_factory.assert_called_once()
        flusher.start.assert_called_once()

def test_real_fork_creates_separate_child_flusher(instrumentation):
    context = multiprocessing.get_context("fork")

    parent_flusher = MagicMock()
    parent_flusher.is_alive = True

    instrumentation._flusher = parent_flusher
    instrumentation._flusher_pid = os.getpid()

    parent_pid = os.getpid()

    receiver, sender = context.Pipe(duplex=False)

    process = context.Process(
        target=_run_flusher_initialization_in_child,
        args=(instrumentation, parent_flusher, sender),
    )

    try:
        process.start()
        sender.close()

        process.join(timeout=5)

        assert not process.is_alive(), "Child process did not exit"
        assert process.exitcode == 0, (
            f"Child process failed with exit code {process.exitcode}"
        )

        assert receiver.poll(), "Child process did not send its result"
        result = receiver.recv()

        assert not process.is_alive(), "Child process did not exit"
        assert process.exitcode == 0
        assert "error" not in result, result

        assert result["pid"] != parent_pid
        assert result["flusher_pid"] == result["pid"]
        assert result["new_flusher_created"] is True
        assert result["flusher_started"] is True

        # The parent must retain its own flusher.
        assert instrumentation._flusher is parent_flusher
        assert instrumentation._flusher_pid == parent_pid

    finally:
        receiver.close()

        if process.is_alive():
            process.terminate()
            process.join(timeout=5)