import logging
import threading
import time

from app.infrastructure.queues import CeleryEmbeddingJobQueue
from app.worker.celery_app import EMBED_PROFILE_TASK


class FakeCeleryApp:
    """Stands in for Celery: `send_task` records the call, then fails or blocks if asked to."""

    def __init__(self, error: Exception | None = None, block_seconds: float = 0.0) -> None:
        self.error = error
        self.block_seconds = block_seconds
        self.calls: list[tuple[str, dict]] = []

    def send_task(self, name: str, **kwargs) -> None:
        self.calls.append((name, kwargs))
        if self.block_seconds:
            time.sleep(self.block_seconds)
        if self.error is not None:
            raise self.error


def _queue(app: FakeCeleryApp, timeout_seconds: float = 1.0) -> CeleryEmbeddingJobQueue:
    return CeleryEmbeddingJobQueue(app, queue_name="embeddings", timeout_seconds=timeout_seconds)


class TestCeleryEmbeddingJobQueue:
    async def test_sends_the_task_to_the_embeddings_queue_without_retries(self):
        app = FakeCeleryApp()

        await _queue(app).enqueue(42)

        assert app.calls == [(EMBED_PROFILE_TASK, {"args": [42], "queue": "embeddings", "retry": False})]

    async def test_send_runs_outside_the_event_loop_thread(self):
        threads: list[int] = []

        class ThreadRecordingApp(FakeCeleryApp):
            def send_task(self, name: str, **kwargs) -> None:
                threads.append(threading.get_ident())

        await _queue(ThreadRecordingApp()).enqueue(1)

        assert threads != [threading.get_ident()]

    async def test_broker_error_is_logged_and_not_raised(self, caplog):
        app = FakeCeleryApp(error=ConnectionError("broker is down"))

        with caplog.at_level(logging.WARNING):
            await _queue(app).enqueue(42)

        assert "Could not enqueue the embedding job for profile 42" in caplog.text

    async def test_hanging_broker_does_not_hold_the_caller_past_the_timeout(self, caplog):
        app = FakeCeleryApp(block_seconds=1.0)

        started = time.monotonic()
        with caplog.at_level(logging.WARNING):
            await _queue(app, timeout_seconds=0.05).enqueue(42)

        assert time.monotonic() - started < 0.5
        assert "Could not enqueue the embedding job for profile 42" in caplog.text
