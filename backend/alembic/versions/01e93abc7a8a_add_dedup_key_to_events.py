"""add dedup_key to events

Revision ID: 01e93abc7a8a
Revises: 0004
Create Date: 2026-08-25 13:16:18.778132
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '01e93abc7a8a'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('dedup_key', sa.String(512), nullable=True))
    op.create_index('ix_events_dedup_key', 'events', ['dedup_key'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_events_dedup_key', table_name='events')
    op.drop_column('events', 'dedup_key')
