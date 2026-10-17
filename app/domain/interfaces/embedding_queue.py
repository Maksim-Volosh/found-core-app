from abc import ABC, abstractmethod


class IEmbeddingJobQueue(ABC):
    @abstractmethod
    async def enqueue(self, profile_id: int) -> None:
        """Never raises: the profile is already saved, and a broker outage must not fail the request.

        A job that was not scheduled is picked up later by the sweep.
        """
