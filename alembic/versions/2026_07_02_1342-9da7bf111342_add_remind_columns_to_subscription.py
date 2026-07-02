from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9da7bf111342"
down_revision: Union[str, Sequence[str], None] = "bd4dcdd07854"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "subscription",
        sa.Column(
            "reminded_7_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "subscription",
        sa.Column(
            "reminded_3_days",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("subscription", "reminded_3_days")
    op.drop_column("subscription", "reminded_7_days")
