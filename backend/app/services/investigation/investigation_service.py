from __future__ import annotations

import uuid
from datetime import datetime, timezone
from math import ceil
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.investigation import Investigation, InvestigationState, InvestigationStatus
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationResponse,
    InvestigationListResponse,
    InvestigationStateTransition,
)

logger = get_logger(__name__)


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


# Valid state transitions
VALID_TRANSITIONS: dict[InvestigationState, set[InvestigationState]] = {
    InvestigationState.OBSERVE: {InvestigationState.QUERY, InvestigationState.FAILED},
    InvestigationState.QUERY: {InvestigationState.CORRELATE, InvestigationState.FAILED},
    InvestigationState.CORRELATE: {InvestigationState.DIAGNOSE, InvestigationState.FAILED},
    InvestigationState.DIAGNOSE: {InvestigationState.COMPLETED, InvestigationState.FAILED},
    InvestigationState.COMPLETED: set(),
    InvestigationState.FAILED: set(),
}


class InvestigationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_investigation(self, data: InvestigationCreate) -> Investigation:
        """Create a new investigation."""
        investigation = Investigation(
            incident_id=data.incident_id,
            payment_id=data.payment_id,
            title=data.title,
            description=data.description,
            metadata_=data.metadata_,
            state=InvestigationState.OBSERVE.value,
            status=InvestigationStatus.PENDING.value,
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(investigation)
        await self.db.flush()
        await self.db.refresh(investigation)

        logger.info(
            "investigation_created",
            extra={
                "investigation_id": str(investigation.id),
                "incident_id": str(investigation.incident_id),
            },
        )
        return investigation

    async def get_investigation(self, investigation_id: uuid.UUID) -> Investigation | None:
        """Get an investigation by ID."""
        result = await self.db.execute(
            select(Investigation).where(Investigation.id == investigation_id)
        )
        return result.scalar_one_or_none()

    async def list_investigations(
        self,
        incident_id: uuid.UUID | None = None,
        state: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> InvestigationListResponse:
        """List investigations with optional filters."""
        query = select(Investigation)
        count_query = select(func.count()).select_from(Investigation)

        if incident_id:
            query = query.where(Investigation.incident_id == incident_id)
            count_query = count_query.where(Investigation.incident_id == incident_id)
        if state:
            query = query.where(Investigation.state == state)
            count_query = count_query.where(Investigation.state == state)
        if status:
            query = query.where(Investigation.status == status)
            count_query = count_query.where(Investigation.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Investigation.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return InvestigationListResponse(
            items=[InvestigationResponse.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            pages=ceil(total / page_size) if total else 0,
        )

    async def transition(
        self,
        investigation_id: uuid.UUID,
        target_state: str,
        data: dict | None = None,
    ) -> Investigation:
        """Transition an investigation to a new state."""
        investigation = await self.get_investigation(investigation_id)
        if not investigation:
            raise ValueError("Investigation not found")

        current_state = InvestigationState(investigation.state)
        new_state = InvestigationState(target_state)

        if new_state not in VALID_TRANSITIONS.get(current_state, set()):
            raise InvalidStateTransitionError(
                f"Cannot transition from {current_state.value} to {new_state.value}"
            )

        investigation.state = new_state.value
        investigation.updated_at = datetime.now(timezone.utc)

        if new_state == InvestigationState.QUERY:
            investigation.status = InvestigationStatus.IN_PROGRESS.value
        elif new_state == InvestigationState.CORRELATE:
            if data and "query_results" in data:
                investigation.query_results = data["query_results"]
        elif new_state == InvestigationState.DIAGNOSE:
            if data and "correlation_results" in data:
                investigation.correlation_results = data["correlation_results"]
        elif new_state == InvestigationState.COMPLETED:
            investigation.status = InvestigationStatus.COMPLETED.value
            investigation.completed_at = datetime.now(timezone.utc)
            if data and "diagnosis" in data:
                investigation.diagnosis = data["diagnosis"]
        elif new_state == InvestigationState.FAILED:
            investigation.status = InvestigationStatus.FAILED.value
            investigation.completed_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(investigation)

        logger.info(
            "investigation_state_transition",
            extra={
                "investigation_id": str(investigation.id),
                "from_state": current_state.value,
                "to_state": new_state.value,
            },
        )
        return investigation

    async def update_investigation(
        self, investigation_id: uuid.UUID, data: InvestigationUpdate
    ) -> Investigation | None:
        """Update an investigation."""
        investigation = await self.get_investigation(investigation_id)
        if not investigation:
            return None

        if data.state is not None:
            investigation = await self.transition(investigation_id, data.state)
        if data.status is not None:
            investigation.status = data.status
        if data.description is not None:
            investigation.description = data.description
        if data.query_results is not None:
            investigation.query_results = data.query_results
        if data.correlation_results is not None:
            investigation.correlation_results = data.correlation_results
        if data.diagnosis is not None:
            investigation.diagnosis = data.diagnosis
        if data.metadata_ is not None:
            investigation.metadata_ = data.metadata_

        investigation.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(investigation)

        logger.info(
            "investigation_updated",
            extra={"investigation_id": str(investigation.id)},
        )
        return investigation

    async def get_state_history(
        self, investigation_id: uuid.UUID
    ) -> list[InvestigationStateTransition]:
        """Get the state transition history for an investigation."""
        investigation = await self.get_investigation(investigation_id)
        if not investigation:
            return []

        history = []
        metadata = investigation.metadata_ or {}
        transitions = metadata.get("transitions", [])

        for transition in transitions:
            history.append(
                InvestigationStateTransition(
                    from_state=transition["from_state"],
                    to_state=transition["to_state"],
                    timestamp=datetime.fromisoformat(transition["timestamp"]),
                    details=transition.get("details"),
                )
            )

        return history
