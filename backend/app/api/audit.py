from __future__ import annotations

import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogCreate, AuditLogResponse
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count()).select_from(AuditLog)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "actor": log.actor or "system",
            "description": log.description or f"{log.action} on {log.resource_type or 'resource'}",
            "resource_type": log.resource_type or "",
            "resource_id": str(log.resource_id) if log.resource_id else "",
            "result": "success",
            "policy_name": None,
            "payload": log.payload or {},
        }
        for log in items
    ]


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
