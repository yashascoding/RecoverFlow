from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse,
    AlertTestRequest,
    AlertTestResponse,
)
from app.services.alert.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    body: AlertCreate,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Create a new alert."""
    svc = AlertService(db)
    alert = await svc.create_alert(body)
    return AlertResponse.model_validate(alert)


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    alert_status: str | None = Query(None, alias="status"),
    severity: str | None = None,
    alert_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List alerts with optional filters."""
    svc = AlertService(db)
    return await svc.list_alerts(
        status=alert_status,
        severity=severity,
        alert_type=alert_type,
        page=page,
        page_size=page_size,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Get an alert by ID."""
    svc = AlertService(db)
    alert = await svc.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    body: AlertUpdate,
    db: AsyncSession = Depends(get_db),
) -> AlertResponse:
    """Update an alert."""
    svc = AlertService(db)
    alert = await svc.update_alert(alert_id, body)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)


@router.post("/test", response_model=AlertTestResponse)
async def test_alert(
    body: AlertTestRequest,
    db: AsyncSession = Depends(get_db),
) -> AlertTestResponse:
    """Test if a metric value would trigger an alert."""
    svc = AlertService(db)
    try:
        return await svc.test_alert(body.alert_id, body.metric_value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
