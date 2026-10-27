import httpx

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.exceptions import EmbeddingProviderUnavailableError, EmbeddingRejectedError
from app.domain.interfaces import IEmbeddingProvider


class OpenAIEmbeddingProvider(IEmbeddingProvider):
    """Calls `POST {base_url}/embeddings`. `transport` is None in production; tests pass httpx.MockTransport."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(
                    "/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={"model": self._model, "input": text},
                )
        except httpx.RequestError as error:
            raise EmbeddingProviderUnavailableError() from error

        if response.status_code == 429 or response.status_code >= 500:
            raise EmbeddingProviderUnavailableError()
        if response.status_code != 200:
            raise EmbeddingRejectedError()

        try:
            vector = [float(value) for value in response.json()["data"][0]["embedding"]]
        except (ValueError, KeyError, IndexError, TypeError) as error:
            raise EmbeddingRejectedError() from error
        if len(vector) != EMBEDDING_DIMENSIONS:
            raise EmbeddingRejectedError()
        return vector
