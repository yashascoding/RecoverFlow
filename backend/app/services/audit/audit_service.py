from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit_log import AuditLog

logger = get_logger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        actor: str | None = None,
        action: str = "",
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        description: str | None = None,
        payload: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        log = AuditLog(
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        logger.info(
            "audit_log_created",
            extra={"log_id": str(log.id), "action": action, "resource_type": resource_type},
        )
        return log

    async def get_by_id(self, log_id: uuid.UUID) -> AuditLog | None:
        result = await self.db.execute(
            select(AuditLog).where(AuditLog.id == log_id)
        )
        return result.scalar_one_or_none()

    async def list_by_resource(
        self, resource_type: str, resource_id: uuid.UUID
    ) -> Sequence[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.resource_type == resource_type)
            .where(AuditLog.resource_id == resource_id)
            .order_by(AuditLog.created_at.desc())
        )
        return result.scalars().all()
