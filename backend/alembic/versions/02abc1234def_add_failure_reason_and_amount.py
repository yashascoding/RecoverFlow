"""add failure_reason to payments and amount to recovery_attempts

Revision ID: 02abc1234def
Revises: 01e93abc7a8a
Create Date: 2026-08-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '02abc1234def'
down_revision: Union[str, None] = '01e93abc7a8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('payments', sa.Column('failure_reason', sa.Text, nullable=True))
    op.add_column('recovery_attempts', sa.Column('amount', sa.Integer, nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('recovery_attempts', 'amount')
    op.drop_column('payments', 'failure_reason')
