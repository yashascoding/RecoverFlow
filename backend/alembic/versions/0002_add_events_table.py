"""add events table

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id", postgresql.UUID(as_uuid=True),
            unique=True, nullable=False,
            comment="Idempotency key — duplicate events share this value",
        ),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column(
            "aggregate_id", postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="ID of the entity this event relates to",
        ),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
    )
    op.create_index("ix_events_event_id", "events", ["event_id"], unique=True)
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_aggregate_id", "events", ["aggregate_id"])
    op.create_index("ix_events_status", "events", ["status"])
    op.create_index("ix_events_created_at", "events", ["created_at"])


def downgrade() -> None:
    op.drop_table("events")
