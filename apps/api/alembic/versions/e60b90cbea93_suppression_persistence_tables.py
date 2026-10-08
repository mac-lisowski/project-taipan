"""suppression persistence tables

Revision ID: e60b90cbea93
Revises: c5dab48db2ae
Create Date: 2026-10-07 16:54:03.990600

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e60b90cbea93'
down_revision: Union[str, Sequence[str], None] = 'c5dab48db2ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('email_suppressions',
    sa.Column('address', sa.Text(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('soft_bounces', sa.Integer(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('address'),
    sa.CheckConstraint("reason IN ('hard', 'soft-limit', 'complaint')",
                       name='ck_email_suppressions_reason'),
    )
    op.create_table('email_send_counters',
    sa.Column('recipient', sa.Text(), nullable=False),
    sa.Column('template', sa.Text(), nullable=False),
    sa.Column('sent_count', sa.BigInteger(), server_default='0', nullable=False),
    sa.PrimaryKeyConstraint('recipient', 'template'),
    )
    op.create_table('email_webhook_events',
    sa.Column('event_id', sa.Text(), nullable=False),
    sa.Column('received_at', sa.DateTime(timezone=True),
              server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('event_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('email_webhook_events')
    op.drop_table('email_send_counters')
    op.drop_table('email_suppressions')
