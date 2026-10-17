"""profile_embeddings

Revision ID: 7c1e5a9b3d42
Revises: ca773380d102
Create Date: 2026-10-17 15:30:12.481936

"""
from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c1e5a9b3d42'
down_revision: Union[str, Sequence[str], None] = 'ca773380d102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate doesn't emit extensions; the vector column and the HNSW index need this one.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('profile_embeddings',
    sa.Column('profile_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.VECTOR(dim=1536), nullable=True),
    sa.Column('input_hash', sa.String(length=64), nullable=True),
    sa.Column('model', sa.String(length=64), nullable=True),
    sa.Column('status', sa.Enum('pending', 'ready', 'failed', name='embedding_status'), nullable=False),
    sa.Column('source_updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], name=op.f('fk_profile_embeddings_profile_id_profiles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('profile_id', name=op.f('pk_profile_embeddings'))
    )
    # Written by hand: autogenerate can lose the operator class of a pgvector index (pgvector-python #118).
    op.create_index('ix_profile_embeddings_embedding_hnsw', 'profile_embeddings', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_profile_embeddings_status_updated_at', 'profile_embeddings', ['status', 'updated_at'], unique=False, postgresql_where=sa.text("status <> 'ready'"))

    # The one place where a revision carries data: profiles that exist already get a pending row,
    # so the sweep embeds them. Without it they would never get a vector.
    op.execute(
        "INSERT INTO profile_embeddings (profile_id, status, source_updated_at, updated_at) "
        "SELECT id, 'pending', updated_at, now() FROM profiles"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_profile_embeddings_status_updated_at', table_name='profile_embeddings', postgresql_where=sa.text("status <> 'ready'"))
    op.drop_index('ix_profile_embeddings_embedding_hnsw', table_name='profile_embeddings', postgresql_using='hnsw', postgresql_with={'m': 16, 'ef_construction': 64}, postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_table('profile_embeddings')

    # drop_table leaves PG enum types behind, which would make the next upgrade fail.
    # The vector extension is deliberately kept: it is a shared extension, not owned by this revision.
    op.execute("DROP TYPE embedding_status")
