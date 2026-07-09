"""Add screening status to user

Revision ID: 23e5d13ed5c0
Revises: b1c2ae265884
Create Date: 2026-07-09 15:21:20.928464

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "23e5d13ed5c0"
down_revision: Union[str, Sequence[str], None] = "b1c2ae265884"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "user",
        sa.Column(
            "screening_status",
            sa.Enum("NOT_STARTED", "APPROVED", name="screeningstatus"),
            nullable=True, # Временно разрешаем NULL
        ),
    )
    
    op.execute("UPDATE \"user\" SET screening_status = 'NOT_STARTED' WHERE screening_status IS NULL")
    
    op.alter_column(
        "user",
        "screening_status",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user", "screening_status")
    sa.Enum(name="screeningstatus").drop(op.get_bind(), checkfirst=False)
