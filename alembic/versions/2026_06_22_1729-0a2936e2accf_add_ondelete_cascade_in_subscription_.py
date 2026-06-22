from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0a2936e2accf"
down_revision: Union[str, Sequence[str], None] = "12d115c8caf9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        op.f("fk_subscription_user_id_user"),
        "subscription",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_subscription_user_id_user"),
        "subscription",
        "user",
        ["user_id"],
        ["user_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("fk_subscription_user_id_user"),
        "subscription",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("fk_subscription_user_id_user"),
        "subscription",
        "user",
        ["user_id"],
        ["user_id"],
    )