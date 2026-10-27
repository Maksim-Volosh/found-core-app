from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.constants import EMBEDDING_DIMENSIONS
from app.domain.enums import EmbeddingStatus
from app.infrastructure.models.base import Base


class ProfileEmbeddingModel(Base):
    __tablename__ = "profile_embeddings"
    __table_args__ = (
        Index(
            "ix_profile_embeddings_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
            postgresql_with={"m": 16, "ef_construction": 64},
        ),
        # Only rows that still need work: the sweep scans this index, and `ready` rows are the vast majority.
        Index(
            "ix_profile_embeddings_status_updated_at",
            "status",
            "updated_at",
            postgresql_where=text("status <> 'ready'"),
        ),
    )

    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True, autoincrement=False
    )
    # Deferred: a plain `select(ProfileEmbeddingModel)` must not drag 1536 floats along. Queries that need it name it.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True, deferred=True
    )
    input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[EmbeddingStatus] = mapped_column(
        Enum(EmbeddingStatus, name="embedding_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
