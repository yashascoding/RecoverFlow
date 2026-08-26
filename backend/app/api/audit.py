from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.audit import AuditLogCreate, AuditLogResponse
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    body: AuditLogCreate,
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    svc = AuditService(db)
    log = await svc.create(
        actor=body.actor,
        action=body.action.value,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        description=body.description,
        payload=body.payload,
        ip_address=body.ip_address,
    )
    await db.commit()
    return AuditLogResponse.model_validate(log)


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AuditLogResponse:
    svc = AuditService(db)
    log = await svc.get_by_id(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found",
        )
    return AuditLogResponse.model_validate(log)


@router.get("/resource/{resource_type}/{resource_id}", response_model=list[AuditLogResponse])
async def list_audit_logs_by_resource(
    resource_type: str,
    resource_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogResponse]:
    svc = AuditService(db)
    logs = await svc.list_by_resource(resource_type, resource_id)
    return [AuditLogResponse.model_validate(l) for l in logs]
