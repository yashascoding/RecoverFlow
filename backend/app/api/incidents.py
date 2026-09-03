from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.incident import (
    IncidentCreate,
    IncidentUpdate,
    IncidentResponse,
    IncidentListResponse,
    IncidentStatsResponse,
)
from app.services.incident.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("/", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    body: IncidentCreate,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Create a new incident."""
    svc = IncidentService(db)
    incident = await svc.create_incident(body)
    return IncidentResponse.model_validate(incident)


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    incident_status: str | None = Query(None, alias="status"),
    severity: str | None = None,
    incident_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> IncidentListResponse:
    """List incidents with optional filters."""
    svc = IncidentService(db)
    return await svc.list_incidents(
        status=incident_status,
        severity=severity,
        incident_type=incident_type,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=IncidentStatsResponse)
async def get_incident_stats(
    db: AsyncSession = Depends(get_db),
) -> IncidentStatsResponse:
    """Get incident statistics."""
    svc = IncidentService(db)
    return await svc.get_stats()


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Get an incident by ID."""
    svc = IncidentService(db)
    incident = await svc.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: uuid.UUID,
    body: IncidentUpdate,
    db: AsyncSession = Depends(get_db),
) -> IncidentResponse:
    """Update an incident."""
    svc = IncidentService(db)
    incident = await svc.update_incident(incident_id, body)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentResponse.model_validate(incident)
