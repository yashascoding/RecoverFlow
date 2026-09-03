from __future__ import annotations

import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.incident import Incident, IncidentStatus, IncidentSeverity
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    IncidentStatsResponse,
)

logger = get_logger(__name__)


class IncidentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_incident(self, data: IncidentCreate) -> Incident:
        """Create a new incident."""
        incident = Incident(
            title=data.title,
            description=data.description,
            severity=data.severity,
            incident_type=data.incident_type,
            affected_gateway=data.affected_gateway,
            affected_bank=data.affected_bank,
            affected_region=data.affected_region,
            affected_payment_method=data.affected_payment_method,
            failure_reason=data.failure_reason,
            revenue_at_risk=data.revenue_at_risk,
            failure_count=data.failure_count,
            baseline_failure_count=data.baseline_failure_count,
            spike_threshold=data.spike_threshold,
            detected_at=data.detected_at,
            metadata_=data.metadata_,
            status=IncidentStatus.OPEN.value,
        )
        self.db.add(incident)
        await self.db.flush()
        await self.db.refresh(incident)

        logger.info(
            "incident_created",
            extra={
                "incident_id": str(incident.id),
                "severity": incident.severity,
                "type": incident.incident_type,
                "revenue_at_risk": incident.revenue_at_risk,
            },
        )
        return incident

    async def get_incident(self, incident_id: uuid.UUID) -> Incident | None:
        """Get an incident by ID."""
        result = await self.db.execute(
            select(Incident).where(Incident.id == incident_id)
        )
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        status: str | None = None,
        severity: str | None = None,
        incident_type: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> IncidentListResponse:
        """List incidents with optional filters."""
        query = select(Incident)
        count_query = select(func.count()).select_from(Incident)

        if status:
            query = query.where(Incident.status == status)
            count_query = count_query.where(Incident.status == status)
        if severity:
            query = query.where(Incident.severity == severity)
            count_query = count_query.where(Incident.severity == severity)
        if incident_type:
            query = query.where(Incident.incident_type == incident_type)
            count_query = count_query.where(Incident.incident_type == incident_type)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Incident.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return IncidentListResponse(
            items=[IncidentResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def update_incident(
        self, incident_id: uuid.UUID, data: IncidentUpdate
    ) -> Incident | None:
        """Update an incident."""
        incident = await self.get_incident(incident_id)
        if not incident:
            return None

        if data.status is not None:
            incident.status = data.status
        if data.severity is not None:
            incident.severity = data.severity
        if data.description is not None:
            incident.description = data.description
        if data.resolved_at is not None:
            incident.resolved_at = data.resolved_at
        if data.metadata_ is not None:
            incident.metadata_ = data.metadata_

        incident.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(incident)

        logger.info(
            "incident_updated",
            extra={"incident_id": str(incident.id), "status": incident.status},
        )
        return incident

    async def get_stats(self) -> IncidentStatsResponse:
        """Get incident statistics."""
        total_result = await self.db.execute(select(func.count()).select_from(Incident))
        total = total_result.scalar() or 0

        open_result = await self.db.execute(
            select(func.count()).select_from(Incident).where(
                Incident.status == IncidentStatus.OPEN.value
            )
        )
        open_count = open_result.scalar() or 0

        investigating_result = await self.db.execute(
            select(func.count()).select_from(Incident).where(
                Incident.status == IncidentStatus.INVESTIGATING.value
            )
        )
        investigating_count = investigating_result.scalar() or 0

        resolved_result = await self.db.execute(
            select(func.count()).select_from(Incident).where(
                Incident.status == IncidentStatus.RESOLVED.value
            )
        )
        resolved_count = resolved_result.scalar() or 0

        escalated_result = await self.db.execute(
            select(func.count()).select_from(Incident).where(
                Incident.status == IncidentStatus.ESCALATED.value
            )
        )
        escalated_count = escalated_result.scalar() or 0

        revenue_result = await self.db.execute(
            select(func.sum(Incident.revenue_at_risk)).where(
                Incident.status.in_([
                    IncidentStatus.OPEN.value,
                    IncidentStatus.INVESTIGATING.value,
                ])
            )
        )
        total_revenue_at_risk = revenue_result.scalar() or 0

        by_severity_result = await self.db.execute(
            select(Incident.severity, func.count(Incident.id)).group_by(Incident.severity)
        )
        by_severity = {row[0]: row[1] for row in by_severity_result.all()}

        by_type_result = await self.db.execute(
            select(Incident.incident_type, func.count(Incident.id)).group_by(Incident.incident_type)
        )
        by_type = {row[0]: row[1] for row in by_type_result.all()}

        return IncidentStatsResponse(
            total_incidents=total,
            open_incidents=open_count,
            investigating_incidents=investigating_count,
            resolved_incidents=resolved_count,
            escalated_incidents=escalated_count,
            total_revenue_at_risk=total_revenue_at_risk,
            by_severity=by_severity,
            by_type=by_type,
        )
