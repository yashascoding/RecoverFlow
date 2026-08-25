"""initial schema — all 11 tables

Revision ID: 0001
Revises:
Create Date: 2026-08-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- customers ---
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_status", "customers", ["status"])
    op.create_index("ix_customers_created_at", "customers", ["created_at"])

    # --- email_templates ---
    op.create_table(
        "email_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("body_html", sa.Text, nullable=False),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("variables", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_templates_name", "email_templates", ["name"], unique=True)

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("razorpay_order_id", sa.String(255), unique=True, nullable=False),
        sa.Column("razorpay_payment_id", sa.String(255), nullable=True, unique=True),
        sa.Column("customer_email", sa.String(320), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("amount", sa.Integer, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("status", sa.String(50), nullable=False, server_default="created"),
        sa.Column("recovery_email_sent", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recovery_email_opened", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payment_link_clicked", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_created_at", "payments", ["created_at"])
    op.create_index("ix_payments_customer_email", "payments", ["customer_email"])

    # --- payment_events ---
    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("razorpay_event_id", sa.String(255), nullable=True, unique=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payment_events_payment_id", "payment_events", ["payment_id"])
    op.create_index("ix_payment_events_event_type", "payment_events", ["event_type"])
    op.create_index("ix_payment_events_created_at", "payment_events", ["created_at"])

    # --- email_messages ---
    op.create_table(
        "email_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True),
        sa.Column("direction", sa.String(50), nullable=False, server_default="outbound"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("recipient_email", sa.String(320), nullable=False),
        sa.Column("sender_email", sa.String(320), nullable=True),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_messages_customer_id", "email_messages", ["customer_id"])
    op.create_index("ix_email_messages_status", "email_messages", ["status"])
    op.create_index("ix_email_messages_direction", "email_messages", ["direction"])
    op.create_index("ix_email_messages_provider_message_id", "email_messages", ["provider_message_id"])
    op.create_index("ix_email_messages_created_at", "email_messages", ["created_at"])

    # --- customer_email_consent ---
    op.create_table(
        "customer_email_consent",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("consent_status", sa.String(50), nullable=False, server_default="granted"),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("customer_id", "channel", name="uq_customer_channel_consent"),
    )
    op.create_index("ix_customer_email_consent_customer_id", "customer_email_consent", ["customer_id"])
    op.create_index("ix_customer_email_consent_channel", "customer_email_consent", ["channel"])
    op.create_index("ix_customer_email_consent_status", "customer_email_consent", ["consent_status"])

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("input_data", postgresql.JSONB, nullable=True),
        sa.Column("output_data", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_runs_agent_type", "agent_runs", ["agent_type"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_payment_id", "agent_runs", ["payment_id"])
    op.create_index("ix_agent_runs_customer_id", "agent_runs", ["customer_id"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])

    # --- agent_actions ---
    op.create_table(
        "agent_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("target", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_actions_run_id", "agent_actions", ["run_id"])
    op.create_index("ix_agent_actions_action_type", "agent_actions", ["action_type"])
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"])

    # --- policy_decisions ---
    op.create_table(
        "policy_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("decision_type", sa.String(50), nullable=False),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("context", postgresql.JSONB, nullable=True),
        sa.Column("evaluated_by", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_policy_decisions_decision_type", "policy_decisions", ["decision_type"])
    op.create_index("ix_policy_decisions_outcome", "policy_decisions", ["outcome"])
    op.create_index("ix_policy_decisions_payment_id", "policy_decisions", ["payment_id"])
    op.create_index("ix_policy_decisions_customer_id", "policy_decisions", ["customer_id"])
    op.create_index("ix_policy_decisions_created_at", "policy_decisions", ["created_at"])

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor", sa.String(255), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # --- recovery_attempts ---
    op.create_table(
        "recovery_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default="1"),
        sa.Column("email_message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("email_messages.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recovery_link", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_recovery_attempts_customer_id", "recovery_attempts", ["customer_id"])
    op.create_index("ix_recovery_attempts_payment_id", "recovery_attempts", ["payment_id"])
    op.create_index("ix_recovery_attempts_status", "recovery_attempts", ["status"])
    op.create_index("ix_recovery_attempts_channel", "recovery_attempts", ["channel"])
    op.create_index("ix_recovery_attempts_created_at", "recovery_attempts", ["created_at"])


def downgrade() -> None:
    op.drop_table("recovery_attempts")
    op.drop_table("audit_logs")
    op.drop_table("policy_decisions")
    op.drop_table("agent_actions")
    op.drop_table("agent_runs")
    op.drop_table("customer_email_consent")
    op.drop_table("email_messages")
    op.drop_table("payment_events")
    op.drop_table("payments")
    op.drop_table("email_templates")
    op.drop_table("customers")
