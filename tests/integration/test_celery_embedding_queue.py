import base64
import json
import logging
import time

from celery import Celery

from app.core.config import settings
from app.infrastructure.queues import CeleryEmbeddingJobQueue
from app.worker.celery_app import EMBED_PROFILE_TASK, celery_app


async def test_enqueue_puts_the_task_on_the_embeddings_queue(broker_client):
    # A generous timeout: this test checks what is sent, not how fast (the timeout has its own unit test).
    queue = CeleryEmbeddingJobQueue(celery_app, settings.embedding.queue_name, timeout_seconds=5.0)

    await queue.enqueue(42)

    messages = await broker_client.lrange(settings.embedding.queue_name, 0, -1)
    assert len(messages) == 1
    message = json.loads(messages[0])
    assert message["headers"]["task"] == EMBED_PROFILE_TASK
    args, kwargs, _ = json.loads(base64.b64decode(message["body"]))
    assert (args, kwargs) == ([42], {})


async def test_unreachable_broker_is_logged_and_does_not_raise(caplog):
    dead_app = Celery("dead", broker="redis://127.0.0.1:1/0")
    dead_app.conf.update(
        broker_connection_timeout=0.2,
        broker_transport_options={"socket_connect_timeout": 0.2},
    )
    queue = CeleryEmbeddingJobQueue(dead_app, settings.embedding.queue_name, timeout_seconds=2.0)

    started = time.monotonic()
    with caplog.at_level(logging.WARNING):
        await queue.enqueue(42)

    assert time.monotonic() - started < 5
    assert "Could not enqueue the embedding job for profile 42" in caplog.text
