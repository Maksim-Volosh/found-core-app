from dataclasses import dataclass
from datetime import datetime

from app.domain.enums import EmbeddingStatus


@dataclass
class ProfileEmbeddingEntity:
    """State of a profile's embedding. The vector itself is deliberately not part of it."""

    profile_id: int
    # `input_hash` and `model` are set if and only if a vector has been stored.
    input_hash: str | None
    model: str | None
    status: EmbeddingStatus
    # Copy of `ProfileEntity.updated_at` taken when the row was last marked pending. Worker writes are conditional on it.
    source_updated_at: datetime
    updated_at: datetime
