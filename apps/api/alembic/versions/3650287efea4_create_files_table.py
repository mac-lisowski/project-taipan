"""create files table

Revision ID: 3650287efea4
Revises: 706345e37b27
Create Date: 2026-10-10 15:38:45.395515

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3650287efea4"
down_revision: str | Sequence[str] | None = "706345e37b27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "files",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("scope IN ('user', 'tenant')", name="ck_files_scope"),
        sa.CheckConstraint(
            "scope = 'tenant' OR created_by_user_id IS NOT NULL",
            name="ck_files_private_has_uploader",
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_files_size_bytes"),
        sa.CheckConstraint("LENGTH(sha256) = 64", name="ck_files_sha256_len"),
        # Attribution, not a delete trigger: RESTRICT forces user deletes
        # through the files service so no S3 object is orphaned.
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bucket", "object_key", name="uq_files_bucket_object_key"),
    )
    op.create_index(
        "ix_files_uploader_tenant_created",
        "files",
        ["created_by_user_id", "tenant_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_files_tenant_created",
        "files",
        ["tenant_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("scope = 'tenant'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_files_tenant_created", table_name="files")
    op.drop_index("ix_files_uploader_tenant_created", table_name="files")
    op.drop_table("files")
