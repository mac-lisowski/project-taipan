"""create tenancy tables

Revision ID: a029aa189a91
Revises: 7100c73337f1
Create Date: 2026-11-19

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a029aa189a91"
down_revision: str | Sequence[str] | None = "7100c73337f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tenants",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_tenants_user_id"), "user_tenants", ["user_id"], unique=True)
    op.create_table(
        "sessions",
        sa.Column("token_sha256", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_sha256"),
    )
    op.create_index(op.f("ix_sessions_user_id"), "sessions", ["user_id"], unique=False)

    # One personal tenant + link row per existing user.
    bind = op.get_bind()
    for (uid,) in bind.execute(sa.text("SELECT id FROM users")).fetchall():
        tid = uuid.uuid4().hex
        bind.execute(sa.text("INSERT INTO tenants (id) VALUES (:tid)"), {"tid": tid})
        bind.execute(
            sa.text("INSERT INTO user_tenants (user_id, tenant_id) VALUES (:uid, :tid)"),
            {"uid": uid, "tid": tid},
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_sessions_user_id"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_index(op.f("ix_user_tenants_user_id"), table_name="user_tenants")
    op.drop_table("user_tenants")
    op.drop_table("tenants")
