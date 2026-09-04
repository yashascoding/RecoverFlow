"""Add user_id to payments for multi-tenancy

Revision ID: 05e1f2a3b4c6
Revises: 04a1b2c3d4e5
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "05e1f2a3b4c6"
down_revision = "04a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_column("payments", "user_id")
