from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.customer import Customer
from app.models.payment import Payment, PaymentStatus
from app.services.recovery.failure_diagnosis import FailureDiagnosisEngine

logger = get_logger(__name__)

diagnosis_engine = FailureDiagnosisEngine()


class CustomerNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Customer not found: {identifier}")
        self.identifier = identifier


class PaymentNotFoundError(Exception):
    def __init__(self, identifier: str) -> None:
        super().__init__(f"Payment not found: {identifier}")
        self.identifier = identifier


class InvalidPaymentStateError(Exception):
    def __init__(self, payment_id: str, status: str) -> None:
        super().__init__(f"Payment {payment_id} is in invalid state: {status}")
        self.payment_id = payment_id
        self.status = status


class DuplicateRecoveryLinkError(Exception):
    def __init__(self, payment_id: str) -> None:
        super().__init__(f"Recovery link already exists for payment {payment_id}")
        self.payment_id = payment_id


class RecoveryServiceV2:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── get_customer ────────────────────────────────────────────────────
    async def get_customer(self, customer_id: uuid.UUID) -> Customer:
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise CustomerNotFoundError(str(customer_id))
        return customer

    async def get_customer_by_email(self, email: str) -> Customer:
        if not email or "@" not in email:
            raise ValueError(f"Invalid email: {email}")
        result = await self.db.execute(
            select(Customer).where(Customer.email == email)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise CustomerNotFoundError(email)
        return customer

    # ── get_payment ─────────────────────────────────────────────────────
    async def get_payment(self, payment_id: uuid.UUID) -> Payment:
        result = await self.db.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise PaymentNotFoundError(str(payment_id))
        return payment

    async def get_payment_by_order(self, order_id: str) -> Payment:
        if not order_id:
            raise ValueError("order_id is required")
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise PaymentNotFoundError(order_id)
        return payment

    async def get_payment_in_state(
        self, payment_id: uuid.UUID, *allowed_states: str
    ) -> Payment:
        payment = await self.get_payment(payment_id)
        if allowed_states and payment.status not in allowed_states:
            raise InvalidPaymentStateError(str(payment.id), payment.status)
        return payment

    # ── get_payment_history ─────────────────────────────────────────────
    async def get_payment_history(
        self,
        customer_id: uuid.UUID,
        *,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Payment]:
        query = select(Payment).where(Payment.customer_id == customer_id)
        if status:
            query = query.where(Payment.status == status)
        query = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_payment_history_count(
        self, customer_id: uuid.UUID, *, status: str | None = None
    ) -> int:
        from sqlalchemy import func
        query = select(func.count()).select_from(Payment).where(
            Payment.customer_id == customer_id
        )
        if status:
            query = query.where(Payment.status == status)
        result = await self.db.execute(query)
        return result.scalar() or 0

    # ── create_payment_link ─────────────────────────────────────────────
    async def create_payment_link(
        self,
        payment_id: uuid.UUID,
        *,
        amount_override: int | None = None,
        expiry_hours: int = 48,
    ) -> dict:
        payment = await self.get_payment_in_state(
            payment_id,
            PaymentStatus.FAILED.value,
            PaymentStatus.RECOVERY_PENDING.value,
        )

        # Prevent duplicate recovery links
        if payment.metadata_ and payment.metadata_.get("recovery_link"):
            raise DuplicateRecoveryLinkError(str(payment_id))

        link_id = uuid.uuid4().hex[:12]
        link_url = f"https://pay.recoverflow.in/retry/{link_id}"

        now = datetime.now(timezone.utc)
        link_data = {
            "link_id": link_id,
            "url": link_url,
            "amount": amount_override or payment.amount,
            "created_at": now.isoformat(),
            "expires_at": now.isoformat(),  # placeholder
            "payment_id": str(payment.id),
        }

        # Store in metadata
        if not payment.metadata_:
            payment.metadata_ = {}
        payment.metadata_["recovery_link"] = link_data
        payment.updated_at = now
        await self.db.flush()

        logger.info(
            "payment_link_created",
            extra={"payment_id": str(payment_id), "link_id": link_id},
        )
        return link_data

    # ── diagnose_failure ────────────────────────────────────────────────
    def diagnose_failure(self, failure_reason: str | None) -> dict:
        result = diagnosis_engine.diagnose(failure_reason)
        return result.to_dict()
