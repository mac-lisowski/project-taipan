"""drop user_roles table

Revision ID: 12cb7ee20e8d
Revises: f57a78ef14d6
Create Date: 2026-10-07 21:43:07.332020

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "12cb7ee20e8d"
down_revision: str | Sequence[str] | None = "f57a78ef14d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_table("user_roles")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_user_roles_role_allowed"),
        sa.UniqueConstraint("user_id", "role"),
    )
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)
    # A downgraded instance still admits its admins, so the grants move back.
    op.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role) "
            "SELECT DISTINCT user_id, role FROM user_tenant_roles"
        )
    )
