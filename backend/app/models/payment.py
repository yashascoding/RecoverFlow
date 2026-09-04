from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class PaymentStatus(str, enum.Enum):
    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    RECOVERY_PENDING = "recovery_pending"
    REFUNDED = "refunded"
    RECOVERED = "recovered"


VALID_TRANSITIONS: dict[PaymentStatus, set[PaymentStatus]] = {
    PaymentStatus.CREATED: {PaymentStatus.AUTHORIZED, PaymentStatus.FAILED},
    PaymentStatus.AUTHORIZED: {PaymentStatus.CAPTURED, PaymentStatus.FAILED},
    PaymentStatus.CAPTURED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: {PaymentStatus.RECOVERY_PENDING},
    PaymentStatus.RECOVERY_PENDING: {PaymentStatus.RECOVERED, PaymentStatus.FAILED},
    PaymentStatus.REFUNDED: set(),
    PaymentStatus.RECOVERED: set(),
}


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    razorpay_order_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    customer_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amount: Mapped[int] = mapped_column(nullable=False, comment="Amount in paise")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PaymentStatus.CREATED.value,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    recovery_email_sent: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_email_opened: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_link_clicked: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    original_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    assignment_group: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="control or ai"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True, default=dict
    )
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
        Index("ix_payments_status", "status"),
        Index("ix_payments_created_at", "created_at"),
        Index("ix_payments_customer_email", "customer_email"),
        Index("ix_payments_assignment_group", "assignment_group"),
    )

    def __repr__(self) -> str:
        return (
            f"<Payment(id={self.id}, order={self.razorpay_order_id}, "
            f"status={self.status})>"
        )
