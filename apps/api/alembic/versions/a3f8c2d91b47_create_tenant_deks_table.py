"""create tenant_deks table

Revision ID: a3f8c2d91b47
Revises: 459336bcc956
Create Date: 2026-10-05 10:12:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3f8c2d91b47'
down_revision: Union[str, Sequence[str], None] = '459336bcc956'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('tenant_deks',
    sa.Column('tenant_id', sa.Text(), nullable=False),
    sa.Column('key_id', sa.Text(), nullable=False),
    sa.Column('wrapped_dek', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('tenant_id'),
    sa.CheckConstraint('LENGTH(key_id) <= 64', name='ck_tenant_deks_key_id_len'),
    sa.CheckConstraint('LENGTH(wrapped_dek) BETWEEN 20 AND 512',
                       name='ck_tenant_deks_wrapped_dek_len'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('tenant_deks')
