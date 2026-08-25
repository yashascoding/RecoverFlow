from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AgentActionStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentActionType(str, enum.Enum):
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SEND_WHATSAPP = "send_whatsapp"
    RETRY_PAYMENT = "retry_payment"
    UPDATE_STATUS = "update_status"
    LOG_EVENT = "log_event"
    CALL_API = "call_api"


class AgentAction(Base):
    __tablename__ = "agent_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[AgentActionType] = mapped_column(
        Enum(AgentActionType, name="agent_action_type"),
        nullable=False,
    )
    status: Mapped[AgentActionStatus] = mapped_column(
        Enum(AgentActionStatus, name="agent_action_status"),
        nullable=False,
        default=AgentActionStatus.PENDING,
    )
    target: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Target resource/identifier")
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_agent_actions_run_id", "run_id"),
        Index("ix_agent_actions_action_type", "action_type"),
        Index("ix_agent_actions_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AgentAction(id={self.id}, type={self.action_type}, status={self.status})>"
