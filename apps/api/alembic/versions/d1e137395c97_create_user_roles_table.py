"""create user_roles table

Revision ID: d1e137395c97
Revises: a029aa189a91
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e137395c97"
down_revision: str | Sequence[str] | None = "a029aa189a91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role = 'admin'", name="ck_user_roles_role_admin"),
        sa.UniqueConstraint("user_id", "role"),
    )
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=True)

    # The earliest user on an upgraded instance becomes admin.
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT count(*) FROM user_roles")).scalar() == 0:
        earliest = bind.execute(
            sa.text("SELECT id FROM users ORDER BY created_at, id LIMIT 1")
        ).scalar()
        if earliest is not None:
            bind.execute(
                sa.text("INSERT INTO user_roles (user_id, role) VALUES (:uid, 'admin')"),
                {"uid": earliest},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_table("user_roles")
