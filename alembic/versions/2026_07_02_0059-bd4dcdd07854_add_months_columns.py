from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "bd4dcdd07854"
down_revision: Union[str, Sequence[str], None] = "5c5299fa248d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("payment", sa.Column("months", sa.Integer(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("payment", "months")
