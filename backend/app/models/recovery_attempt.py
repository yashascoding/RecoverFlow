from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class RecoveryAttemptStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    CONVERTED = "converted"
    FAILED = "failed"
    EXPIRED = "expired"


class RecoveryChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"


class RecoveryAttempt(Base):
    __tablename__ = "recovery_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[int] = mapped_column(nullable=False, default=0, comment="Amount in paise")
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RecoveryChannel.EMAIL.value,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=RecoveryAttemptStatus.PENDING.value,
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    email_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_messages.id", ondelete="SET NULL"), nullable=True
    )
    recovery_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_recovery_attempts_customer_id", "customer_id"),
        Index("ix_recovery_attempts_payment_id", "payment_id"),
        Index("ix_recovery_attempts_status", "status"),
        Index("ix_recovery_attempts_channel", "channel"),
        Index("ix_recovery_attempts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<RecoveryAttempt(id={self.id}, status={self.status}, attempt={self.attempt_number})>"
