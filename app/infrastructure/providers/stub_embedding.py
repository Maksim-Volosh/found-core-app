import hashlib
import math

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.interfaces import IEmbeddingProvider


class StubEmbeddingProvider(IEmbeddingProvider):
    """Deterministic pseudo-random unit vector derived from the text. Used while there is no OpenAI key.

    The vector has no semantics: similar texts get unrelated vectors. It only lets the rest of the pipeline run.
    """

    @property
    def model(self) -> str:
        return "stub-v1"

    async def embed(self, text: str) -> list[float]:
        raw = hashlib.shake_256(text.encode()).digest(EMBEDDING_DIMENSIONS * 4)
        values = [int.from_bytes(raw[i : i + 4], "big") / 2**31 - 1 for i in range(0, len(raw), 4)]
        norm = math.sqrt(sum(v * v for v in values))
        return [v / norm for v in values]
