from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.services.payments.payment_service import PaymentService

logger = get_logger(__name__)


class RecoveryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payment_service = PaymentService(db)

    async def initiate_recovery(self, order_id: str) -> dict:
        payment = await self.payment_service.get_payment_by_order_id(order_id)
        if not payment:
            raise ValueError(f"Payment not found for order: {order_id}")

        if payment.status not in (
            PaymentStatus.FAILED,
            PaymentStatus.CREATED,
        ):
            raise ValueError(
                f"Cannot initiate recovery for payment in status: {payment.status}"
            )

        payment.recovery_email_sent = datetime.now(timezone.utc)
        payment.status = PaymentStatus.RECOVERED
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(
            "recovery_initiated",
            extra={"order_id": order_id, "payment_id": str(payment.id)},
        )

        return {
            "payment_id": str(payment.id),
            "order_id": order_id,
            "status": "recovery_initiated",
            "recovery_email_sent": payment.recovery_email_sent.isoformat(),
        }

    async def record_recovery_success(self, order_id: str) -> Payment | None:
        payment = await self.payment_service.get_payment_by_order_id(order_id)
        if not payment:
            return None

        payment.status = PaymentStatus.RECOVERED
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(
            "recovery_success_recorded",
            extra={"order_id": order_id},
        )
        return payment

    async def get_recovery_status(self, payment_id: uuid.UUID) -> dict | None:
        payment = await self.payment_service.get_payment_by_id(payment_id)
        if not payment:
            return None

        return {
            "payment_id": str(payment.id),
            "razorpay_order_id": payment.razorpay_order_id,
            "status": payment.status.value,
            "recovery_email_sent": (
                payment.recovery_email_sent.isoformat()
                if payment.recovery_email_sent
                else None
            ),
            "recovery_email_opened": (
                payment.recovery_email_opened.isoformat()
                if payment.recovery_email_opened
                else None
            ),
            "payment_link_clicked": (
                payment.payment_link_clicked.isoformat()
                if payment.payment_link_clicked
                else None
            ),
        }

    async def retry_recovery(self, payment_id: uuid.UUID) -> dict:
        payment = await self.payment_service.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")

        if payment.status == PaymentStatus.RECOVERED:
            raise ValueError("Payment already recovered")

        payment.recovery_email_sent = datetime.now(timezone.utc)
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(
            "recovery_retried",
            extra={"payment_id": str(payment_id)},
        )

        return {
            "payment_id": str(payment.id),
            "status": "recovery_retried",
            "recovery_email_sent": payment.recovery_email_sent.isoformat(),
        }
