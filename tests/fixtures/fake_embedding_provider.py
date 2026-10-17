from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.interfaces import IEmbeddingProvider


class FakeEmbeddingProvider(IEmbeddingProvider):
    """Returns a vector derived from the text length and records every call.

    Set `error` to make the next calls fail the way the real provider does
    (EmbeddingProviderUnavailableError or EmbeddingRejectedError).
    """

    def __init__(self, model: str = "fake-model") -> None:
        self._model = model
        self.calls: list[str] = []
        self.error: Exception | None = None

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, text: str) -> list[float]:
        self.calls.append(text)
        if self.error is not None:
            raise self.error
        return [float(len(text))] + [0.0] * (EMBEDDING_DIMENSIONS - 1)
