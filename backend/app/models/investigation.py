from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class InvestigationState(str, enum.Enum):
    OBSERVE = "observe"
    QUERY = "query"
    CORRELATE = "correlate"
    DIAGNOSE = "diagnose"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InvestigationState.OBSERVE.value,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InvestigationStatus.PENDING.value,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    query_results: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Results from QUERY state"
    )
    correlation_results: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Results from CORRELATE state"
    )
    diagnosis: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Results from DIAGNOSE state"
    )
    
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
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
        Index("ix_investigations_incident_id", "incident_id"),
        Index("ix_investigations_state", "state"),
        Index("ix_investigations_status", "status"),
        Index("ix_investigations_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Investigation(id={self.id}, state={self.state}, "
            f"status={self.status})>"
        )
