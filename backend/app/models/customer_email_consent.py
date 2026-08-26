from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ConsentChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    PUSH = "push"


class ConsentStatus(str, enum.Enum):
    GRANTED = "granted"
    DENIED = "denied"
    REVOKED = "revoked"


class CustomerEmailConsent(Base):
    __tablename__ = "customer_email_consent"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ConsentChannel.EMAIL.value,
    )
    consent_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ConsentStatus.GRANTED.value,
    )
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="e.g. signup_form, webhook, manual")
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
        UniqueConstraint("customer_id", "channel", name="uq_customer_channel_consent"),
        Index("ix_customer_email_consent_customer_id", "customer_id"),
        Index("ix_customer_email_consent_channel", "channel"),
        Index("ix_customer_email_consent_status", "consent_status"),
    )

    def __repr__(self) -> str:
        return f"<CustomerEmailConsent(customer={self.customer_id}, channel={self.channel}, status={self.consent_status})>"
