from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    RESOLVED = "resolved"
    DISABLED = "disabled"


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AlertStatus.ACTIVE.value,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=AlertSeverity.MEDIUM.value,
    )
    alert_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type: failure_rate, revenue_at_risk, spike, etc.",
    )
    metric_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Metric to monitor: failure_rate, revenue_at_risk, etc.",
    )
    threshold_value: Mapped[float] = mapped_column(nullable=False)
    comparison_operator: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Comparison operator: gt, gte, lt, lte, eq",
    )
    time_window_minutes: Mapped[int] = mapped_column(nullable=False, default=60)
    cooldown_minutes: Mapped[int] = mapped_column(nullable=False, default=30)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_value: Mapped[float | None] = mapped_column(nullable=True)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True
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
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_severity", "severity"),
        Index("ix_alerts_alert_type", "alert_type"),
        Index("ix_alerts_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, name={self.name}, "
            f"status={self.status}, severity={self.severity})>"
        )
