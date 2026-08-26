from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus, VALID_TRANSITIONS
from app.services.payments.payment_service import PaymentService

logger = get_logger(__name__)


class InvalidTransitionError(Exception):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid transition: {current} → {target}. "
            f"Valid targets from {current}: {[s.value for s in VALID_TRANSITIONS.get(PaymentStatus(current), set())]}"
        )


class PaymentTransitionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.payment_service = PaymentService(db)

    def validate_transition(self, current: str, target: str) -> None:
        current_status = PaymentStatus(current)
        target_status = PaymentStatus(target)
        valid = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in valid:
            raise InvalidTransitionError(current, target)

    async def transition(
        self,
        payment_id: str,
        target_status: str,
        *,
        failure_reason: str | None = None,
        payment_id_razorpay: str | None = None,
    ) -> Payment:
        payment = await self.payment_service.get_payment_by_order_id(payment_id)
        if not payment:
            payment = await self.payment_service.get_payment_by_id(
                __import__("uuid").UUID(payment_id)
            )
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")

        self.validate_transition(payment.status, target_status)

        old_status = payment.status
        payment.status = target_status
        payment.updated_at = datetime.now(timezone.utc)

        if target_status == PaymentStatus.FAILED.value and failure_reason:
            payment.failure_reason = failure_reason

        if payment_id_razorpay:
            payment.razorpay_payment_id = payment_id_razorpay

        if target_status == PaymentStatus.RECOVERY_PENDING.value:
            payment.recovery_email_sent = datetime.now(timezone.utc)

        await self.db.flush()

        logger.info(
            "payment_transitioned",
            extra={
                "payment_id": str(payment.id),
                "old_status": old_status,
                "new_status": target_status,
            },
        )
        return payment

    async def initiate_recovery(self, order_id: str) -> Payment:
        payment = await self.payment_service.get_payment_by_order_id(order_id)
        if not payment:
            raise ValueError(f"Payment not found: {order_id}")

        self.validate_transition(payment.status, PaymentStatus.RECOVERY_PENDING.value)

        old_status = payment.status
        payment.status = PaymentStatus.RECOVERY_PENDING.value
        payment.recovery_email_sent = datetime.now(timezone.utc)
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(
            "recovery_initiated",
            extra={"order_id": order_id, "old_status": old_status},
        )
        return payment

    async def record_recovery_success(self, order_id: str) -> Payment:
        payment = await self.payment_service.get_payment_by_order_id(order_id)
        if not payment:
            raise ValueError(f"Payment not found: {order_id}")

        self.validate_transition(payment.status, PaymentStatus.RECOVERED.value)

        payment.status = PaymentStatus.RECOVERED.value
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("recovery_success_recorded", extra={"order_id": order_id})
        return payment
