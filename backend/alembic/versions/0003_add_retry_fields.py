"""add retry fields to events

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"))
    op.add_column("events", sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"))
    op.add_column("events", sa.Column("last_error", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("events", "last_error")
    op.drop_column("events", "max_retries")
    op.drop_column("events", "retry_count")
