"""widen user_roles check to member, allow several roles per user

Revision ID: c5dab48db2ae
Revises: d1e137395c97
Create Date: 2026-10-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c5dab48db2ae"
down_revision: str | Sequence[str] | None = "d1e137395c97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_constraint("ck_user_roles_role_admin", "user_roles", type_="check")
    op.create_check_constraint(
        "ck_user_roles_role_allowed",
        "user_roles",
        "role IN ('admin', 'member')",
    )
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=False)

    # Every user holds member by default; admin stays an extra grant.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO user_roles (user_id, role) "
            "SELECT id, 'member' FROM users "
            "WHERE id NOT IN (SELECT user_id FROM user_roles WHERE role = 'member')"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_roles_user_id"), table_name="user_roles")
    op.drop_constraint("ck_user_roles_role_allowed", "user_roles", type_="check")
    op.execute(sa.text("DELETE FROM user_roles WHERE role = 'member'"))
    op.create_check_constraint(
        "ck_user_roles_role_admin",
        "user_roles",
        "role = 'admin'",
    )
    op.create_index(op.f("ix_user_roles_user_id"), "user_roles", ["user_id"], unique=True)
