from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.policy_decision import PolicyDecision

logger = get_logger(__name__)


class PolicyService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        decision_type: str,
        outcome: str,
        payment_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        reason: str | None = None,
        context: dict | None = None,
        evaluated_by: str | None = None,
    ) -> PolicyDecision:
        decision = PolicyDecision(
            decision_type=decision_type,
            outcome=outcome,
            payment_id=payment_id,
            customer_id=customer_id,
            reason=reason,
            context=context,
            evaluated_by=evaluated_by,
        )
        self.db.add(decision)
        await self.db.flush()
        await self.db.refresh(decision)
        logger.info(
            "policy_decision_created",
            extra={"decision_id": str(decision.id), "type": decision_type, "outcome": outcome},
        )
        return decision

    async def get_by_id(self, decision_id: uuid.UUID) -> PolicyDecision | None:
        result = await self.db.execute(
            select(PolicyDecision).where(PolicyDecision.id == decision_id)
        )
        return result.scalar_one_or_none()

    async def list_by_customer(self, customer_id: uuid.UUID) -> Sequence[PolicyDecision]:
        result = await self.db.execute(
            select(PolicyDecision)
            .where(PolicyDecision.customer_id == customer_id)
            .order_by(PolicyDecision.created_at.desc())
        )
        return result.scalars().all()

    async def list_by_payment(self, payment_id: uuid.UUID) -> Sequence[PolicyDecision]:
        result = await self.db.execute(
            select(PolicyDecision)
            .where(PolicyDecision.payment_id == payment_id)
            .order_by(PolicyDecision.created_at.desc())
        )
        return result.scalars().all()
