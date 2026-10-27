import json

import httpx
import pytest

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.exceptions import EmbeddingProviderUnavailableError, EmbeddingRejectedError
from app.infrastructure.providers import OpenAIEmbeddingProvider

VECTOR = [0.25] * EMBEDDING_DIMENSIONS


def _provider(handler) -> OpenAIEmbeddingProvider:
    return OpenAIEmbeddingProvider(
        api_key="sk-test",
        model="text-embedding-3-small",
        base_url="https://api.test/v1",
        timeout_seconds=1.0,
        transport=httpx.MockTransport(handler),
    )


def _ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"data": [{"embedding": VECTOR}]})


async def test_returns_the_vector_from_the_response():
    assert await _provider(_ok).embed("hello") == VECTOR


async def test_sends_the_model_text_and_api_key_to_the_embeddings_endpoint():
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent["url"] = str(request.url)
        sent["auth"] = request.headers["Authorization"]
        sent["body"] = json.loads(request.content)
        return _ok(request)

    await _provider(handler).embed("hello")

    assert sent["url"] == "https://api.test/v1/embeddings"
    assert sent["auth"] == "Bearer sk-test"
    assert sent["body"] == {"model": "text-embedding-3-small", "input": "hello"}


async def test_exposes_the_configured_model():
    assert _provider(_ok).model == "text-embedding-3-small"


@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_rate_limit_and_server_errors_are_temporary(status):
    provider = _provider(lambda request: httpx.Response(status))

    with pytest.raises(EmbeddingProviderUnavailableError):
        await provider.embed("hello")


@pytest.mark.parametrize("error", [httpx.ReadTimeout, httpx.ConnectTimeout, httpx.ConnectError])
async def test_timeouts_and_network_errors_are_temporary(error):
    def handler(request: httpx.Request) -> httpx.Response:
        raise error("failure", request=request)

    with pytest.raises(EmbeddingProviderUnavailableError):
        await _provider(handler).embed("hello")


@pytest.mark.parametrize("status", [400, 401, 403, 404])
async def test_other_client_errors_are_permanent(status):
    provider = _provider(lambda request: httpx.Response(status, json={"error": {"message": "no"}}))

    with pytest.raises(EmbeddingRejectedError):
        await provider.embed("hello")


async def test_a_vector_of_the_wrong_length_is_permanent():
    provider = _provider(lambda request: httpx.Response(200, json={"data": [{"embedding": [0.1] * 3}]}))

    with pytest.raises(EmbeddingRejectedError):
        await provider.embed("hello")


@pytest.mark.parametrize(
    "body",
    [{}, {"data": []}, {"data": [{}]}, {"data": [{"embedding": "text"}]}, {"data": [{"embedding": [None]}]}],
)
async def test_a_malformed_response_is_permanent(body):
    provider = _provider(lambda request: httpx.Response(200, json=body))

    with pytest.raises(EmbeddingRejectedError):
        await provider.embed("hello")


async def test_a_response_that_is_not_json_is_permanent():
    provider = _provider(lambda request: httpx.Response(200, text="<html>gateway</html>"))

    with pytest.raises(EmbeddingRejectedError):
        await provider.embed("hello")
