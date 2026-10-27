from abc import ABC, abstractmethod


class IEmbeddingProvider(ABC):
    @property
    @abstractmethod
    def model(self) -> str:
        """Name of the model the vectors come from. Part of the input hash, so a model change recomputes vectors."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Returns a vector of EMBEDDING_DIMENSIONS floats.

        Raises EmbeddingProviderUnavailableError for a temporary failure (worth retrying)
        and EmbeddingRejectedError for a permanent one (retrying cannot help).
        """
