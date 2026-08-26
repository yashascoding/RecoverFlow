from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PolicyDecisionType(str, enum.Enum):
    RECOVERY_ELIGIBLE = "recovery_eligible"
    CONTACT_ALLOWED = "contact_allowed"
    RETRY_ALLOWED = "retry_allowed"
    QUIET_HOURS_BLOCKED = "quiet_hours_blocked"
    CONSENT_REQUIRED = "consent_required"
    MAX_ATTEMPTS_REACHED = "max_attempts_reached"


class PolicyOutcome(str, enum.Enum):
    APPROVED = "approved"
    DENIED = "denied"
    DEFERRED = "deferred"


class PolicyDecision(Base):
    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    decision_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evaluated_by: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="e.g. policy_engine, agent, manual")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_policy_decisions_decision_type", "decision_type"),
        Index("ix_policy_decisions_outcome", "outcome"),
        Index("ix_policy_decisions_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PolicyDecision(id={self.id}, type={self.decision_type}, outcome={self.outcome})>"
