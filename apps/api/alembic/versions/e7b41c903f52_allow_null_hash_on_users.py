"""allow null hash on users

Revision ID: e7b41c903f52
Revises: b8e4c2a61d05
Create Date: 2026-10-08 11:20:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7b41c903f52"
down_revision: str | Sequence[str] | None = "b8e4c2a61d05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # A half account waits for activation; no password hash exists yet.
    op.alter_column("users", "hashed_password", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column("users", "hashed_password", existing_type=sa.String(), nullable=False)
