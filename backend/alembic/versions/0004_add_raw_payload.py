"""add raw_payload to events

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("raw_payload", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("events", "raw_payload")
