"""add tenant and system grant tables

Revision ID: f57a78ef14d6
Revises: e60b90cbea93
Create Date: 2026-10-07 21:16:56.051837

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f57a78ef14d6"
down_revision: str | Sequence[str] | None = "e60b90cbea93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_tenant_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role IN ('admin', 'member')", name="ck_user_tenant_roles_role_allowed"),
        sa.UniqueConstraint("user_id", "tenant_id", "role"),
    )
    op.create_index(
        op.f("ix_user_tenant_roles_user_id"), "user_tenant_roles", ["user_id"], unique=False
    )
    op.create_table(
        "user_system_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("role IN ('system_owner')", name="ck_user_system_roles_role_allowed"),
        sa.UniqueConstraint("user_id", "role"),
    )
    op.create_index(
        op.f("ix_user_system_roles_user_id"), "user_system_roles", ["user_id"], unique=False
    )

    # Every old grant becomes a tenant role in the user's linked tenant.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO user_tenant_roles (user_id, tenant_id, role) "
            "SELECT ur.user_id, ut.tenant_id, ur.role FROM user_roles ur "
            "JOIN user_tenants ut ON ut.user_id = ur.user_id"
        )
    )
    # The earliest user on an upgraded instance owns the system.
    earliest = bind.execute(
        sa.text("SELECT id FROM users ORDER BY created_at, id LIMIT 1")
    ).scalar()
    if earliest is not None:
        bind.execute(
            sa.text("INSERT INTO user_system_roles (user_id, role) VALUES (:uid, 'system_owner')"),
            {"uid": earliest},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_tenant_roles_user_id"), table_name="user_tenant_roles")
    op.drop_table("user_tenant_roles")
    op.drop_index(op.f("ix_user_system_roles_user_id"), table_name="user_system_roles")
    op.drop_table("user_system_roles")
