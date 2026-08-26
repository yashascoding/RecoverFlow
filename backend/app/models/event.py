from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EventStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), unique=True, nullable=False, index=True,
        comment="Idempotency key — duplicate events share this value",
    )
    event_type: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    aggregate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="ID of the entity this event relates to",
    )
    source: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
    )
    raw_payload: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Original unparsed webhook body from Razorpay",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default="pending",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3,
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    dedup_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True, unique=True, index=True,
        comment="Business-level dedup key, e.g. razorpay:pay_id:event_type",
    )

    __table_args__ = (
        Index("ix_events_status", "status"),
        Index("ix_events_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Event(id={self.id}, type={self.event_type}, "
            f"status={self.status})>"
        )
