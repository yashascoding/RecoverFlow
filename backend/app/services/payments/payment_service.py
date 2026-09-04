from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus

logger = get_logger(__name__)


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_payment_record(
        self,
        order_id: str,
        amount: int,
        currency: str,
        customer_email: str,
        customer_phone: str | None = None,
        metadata: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> Payment:
        payment = Payment(
            razorpay_order_id=order_id,
            amount=amount,
            currency=currency,
            customer_email=customer_email,
            customer_phone=customer_phone,
            status=PaymentStatus.CREATED.value,
            metadata_=metadata,
            user_id=user_id,
        )
        self.db.add(payment)
        await self.db.flush()
        await self.db.refresh(payment)
        logger.info(
            "payment_record_created",
            extra={"order_id": order_id, "payment_id": str(payment.id)},
        )
        return payment

    async def update_payment_status(
        self,
        order_id: str,
        status: PaymentStatus | str,
        payment_id: str | None = None,
    ) -> Payment | None:
        if isinstance(status, str):
            status_value = status
        else:
            status_value = status.value
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            logger.warning("payment_not_found_for_update", extra={"order_id": order_id})
            return None

        old_status = payment.status
        payment.status = status_value
        if payment_id:
            payment.razorpay_payment_id = payment_id
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info(
            "payment_status_updated",
            extra={
                "order_id": order_id,
                "old_status": old_status,
                "new_status": status_value,
            },
        )
        return payment

    async def get_payment_by_id(self, payment_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Payment | None:
        query = select(Payment).where(Payment.id == payment_id)
        if user_id:
            query = query.where(Payment.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_payment_by_order_id(self, order_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(Payment.razorpay_order_id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_razorpay_payment_id(
        self, razorpay_payment_id: str
    ) -> Payment | None:
        result = await self.db.execute(
            select(Payment).where(
                Payment.razorpay_payment_id == razorpay_payment_id
            )
        )
        return result.scalar_one_or_none()

    async def update_payment_link_clicked(self, order_id: str) -> Payment | None:
        payment = await self.get_payment_by_order_id(order_id)
        if not payment:
            return None
        payment.payment_link_clicked = datetime.now(timezone.utc)
        payment.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info("payment_link_clicked", extra={"order_id": order_id})
        return payment

    async def list_payments(
        self,
        status: PaymentStatus | str | None = None,
        customer_email: str | None = None,
        user_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Payment], int]:
        query = select(Payment)
        count_query = select(func.count()).select_from(Payment)

        if user_id:
            query = query.where(Payment.user_id == user_id)
            count_query = count_query.where(Payment.user_id == user_id)
        if status:
            status_value = status.value if isinstance(status, PaymentStatus) else status
            query = query.where(Payment.status == status_value)
            count_query = count_query.where(Payment.status == status_value)
        if customer_email:
            query = query.where(Payment.customer_email == customer_email)
            count_query = count_query.where(Payment.customer_email == customer_email)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Payment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total
