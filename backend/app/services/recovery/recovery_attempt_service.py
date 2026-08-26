from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.recovery_attempt import (
    RecoveryAttempt,
    RecoveryAttemptStatus,
    RecoveryChannel,
)

logger = get_logger(__name__)


class RecoveryAttemptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        customer_id: uuid.UUID,
        payment_id: uuid.UUID,
        channel: str,
        amount: int,
    ) -> RecoveryAttempt:
        attempt = RecoveryAttempt(
            customer_id=customer_id,
            payment_id=payment_id,
            channel=channel,
            amount=amount,
            status=RecoveryAttemptStatus.PENDING.value,
        )
        self.db.add(attempt)
        await self.db.flush()
        await self.db.refresh(attempt)
        logger.info(
            "recovery_attempt_created",
            extra={"attempt_id": str(attempt.id), "payment_id": str(payment_id)},
        )
        return attempt

    async def get_by_id(self, attempt_id: uuid.UUID) -> RecoveryAttempt | None:
        result = await self.db.execute(
            select(RecoveryAttempt).where(RecoveryAttempt.id == attempt_id)
        )
        return result.scalar_one_or_none()

    async def list_by_payment(self, payment_id: uuid.UUID) -> Sequence[RecoveryAttempt]:
        result = await self.db.execute(
            select(RecoveryAttempt)
            .where(RecoveryAttempt.payment_id == payment_id)
            .order_by(RecoveryAttempt.created_at.desc())
        )
        return result.scalars().all()

    async def update_status(
        self, attempt_id: uuid.UUID, status: str
    ) -> RecoveryAttempt | None:
        result = await self.db.execute(
            select(RecoveryAttempt).where(RecoveryAttempt.id == attempt_id)
        )
        attempt = result.scalar_one_or_none()
        if not attempt:
            logger.warning("recovery_attempt_not_found", extra={"attempt_id": str(attempt_id)})
            return None

        old_status = attempt.status
        attempt.status = status
        now = datetime.now(timezone.utc)

        if status == RecoveryAttemptStatus.SENT.value:
            attempt.sent_at = now
        elif status == RecoveryAttemptStatus.OPENED.value:
            attempt.opened_at = now
        elif status == RecoveryAttemptStatus.CLICKED.value:
            attempt.clicked_at = now
        elif status == RecoveryAttemptStatus.CONVERTED.value:
            attempt.converted_at = now
        elif status == RecoveryAttemptStatus.FAILED.value:
            attempt.failed_at = now

        attempt.updated_at = now
        await self.db.flush()
        logger.info(
            "recovery_attempt_status_updated",
            extra={"attempt_id": str(attempt_id), "old_status": old_status, "new_status": status},
        )
        return attempt
