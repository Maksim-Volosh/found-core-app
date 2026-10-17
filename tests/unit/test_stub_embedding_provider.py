import math

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.infrastructure.providers import StubEmbeddingProvider


async def test_the_same_text_gives_the_same_vector():
    provider = StubEmbeddingProvider()

    assert await provider.embed("hello") == await provider.embed("hello")


async def test_different_texts_give_different_vectors():
    provider = StubEmbeddingProvider()

    assert await provider.embed("hello") != await provider.embed("hello!")


async def test_the_vector_has_the_dimension_the_column_expects():
    assert len(await StubEmbeddingProvider().embed("hello")) == EMBEDDING_DIMENSIONS


async def test_the_vector_has_unit_length():
    vector = await StubEmbeddingProvider().embed("hello")

    assert math.isclose(math.sqrt(sum(v * v for v in vector)), 1.0, rel_tol=1e-9)


async def test_the_model_name_differs_from_a_real_model():
    # The name goes into the input hash, so switching from the stub to OpenAI recomputes every vector.
    assert StubEmbeddingProvider().model == "stub-v1"
