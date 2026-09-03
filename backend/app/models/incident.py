from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class IncidentSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IncidentStatus.OPEN.value,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=IncidentSeverity.MEDIUM.value,
    )
    incident_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type: spike, degradation, threshold_exceeded, etc.",
    )
    affected_gateway: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_bank: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    affected_payment_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    revenue_at_risk: Mapped[int] = mapped_column(nullable=False, default=0, comment="Revenue at risk in paise")
    failure_count: Mapped[int] = mapped_column(nullable=False, default=0)
    baseline_failure_count: Mapped[float] = mapped_column(nullable=False, default=0.0)
    spike_threshold: Mapped[float] = mapped_column(nullable=False, default=0.0)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_incident_type", "incident_type"),
        Index("ix_incidents_detected_at", "detected_at"),
        Index("ix_incidents_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Incident(id={self.id}, type={self.incident_type}, "
            f"severity={self.severity}, status={self.status})>"
        )
