import asyncio
import logging

from celery import Celery

from app.domain.interfaces import IEmbeddingJobQueue
from app.worker.celery_app import EMBED_PROFILE_TASK

logger = logging.getLogger(__name__)


class CeleryEmbeddingJobQueue(IEmbeddingJobQueue):
    def __init__(self, celery_app: Celery, queue_name: str, timeout_seconds: float) -> None:
        self._celery_app = celery_app
        self._queue_name = queue_name
        self._timeout_seconds = timeout_seconds

    async def enqueue(self, profile_id: int) -> None:
        # `send_task` is synchronous and, with the broker down, would block the request: it runs in a thread
        # under a timeout, without retries. A timed-out thread finishes on its own once the socket gives up.
        try:
            await asyncio.wait_for(
                asyncio.to_thread(
                    self._celery_app.send_task,
                    EMBED_PROFILE_TASK,
                    args=[profile_id],
                    queue=self._queue_name,
                    retry=False,
                ),
                timeout=self._timeout_seconds,
            )
        except Exception:
            logger.warning("Could not enqueue the embedding job for profile %s", profile_id, exc_info=True)
