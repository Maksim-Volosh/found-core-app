from app.domain.interfaces import IEmbeddingJobQueue


class FakeEmbeddingQueue(IEmbeddingJobQueue):
    """Records the scheduled profile ids. Like the real queue, it never raises."""

    def __init__(self) -> None:
        self.enqueued: list[int] = []

    async def enqueue(self, profile_id: int) -> None:
        self.enqueued.append(profile_id)
