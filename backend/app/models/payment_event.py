from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaymentEventType(str, enum.Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    RECOVERED = "recovered"
    WEBHOOK_RECEIVED = "webhook_received"


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[PaymentEventType] = mapped_column(
        Enum(PaymentEventType, name="payment_event_type"),
        nullable=False,
    )
    razorpay_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_payment_events_payment_id", "payment_id"),
        Index("ix_payment_events_event_type", "event_type"),
        Index("ix_payment_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PaymentEvent(id={self.id}, type={self.event_type})>"
