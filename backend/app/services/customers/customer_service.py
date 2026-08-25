from __future__ import annotations

import uuid
from math import ceil
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.customer import Customer, CustomerStatus

logger = get_logger(__name__)


class CustomerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_customer(
        self,
        email: str,
        name: str | None = None,
        phone: str | None = None,
    ) -> Customer:
        customer = Customer(
            email=email,
            name=name,
            phone=phone,
            status=CustomerStatus.ACTIVE.value,
        )
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        logger.info(
            "customer_created",
            extra={"customer_id": str(customer.id), "email": email},
        )
        return customer

    async def get_customer_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_customer_by_email(self, email: str) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(Customer.email == email)
        )
        return result.scalar_one_or_none()

    async def list_customers(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Customer], int]:
        count_query = select(func.count()).select_from(Customer)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = (
            select(Customer)
            .order_by(Customer.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total
