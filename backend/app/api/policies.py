from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.policy import PolicyDecisionCreate, PolicyDecisionResponse
from app.services.policy.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


@router.post("/", response_model=PolicyDecisionResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_decision(
    body: PolicyDecisionCreate,
    db: AsyncSession = Depends(get_db),
) -> PolicyDecisionResponse:
    svc = PolicyService(db)
    decision = await svc.create(
        decision_type=body.decision_type.value,
        outcome=body.outcome.value,
        payment_id=body.payment_id,
        customer_id=body.customer_id,
        reason=body.reason,
        context=body.context,
        evaluated_by=body.evaluated_by,
    )
    await db.commit()
    return PolicyDecisionResponse.model_validate(decision)


@router.get("/{decision_id}", response_model=PolicyDecisionResponse)
async def get_policy_decision(
    decision_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PolicyDecisionResponse:
    svc = PolicyService(db)
    decision = await svc.get_by_id(decision_id)
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy decision not found",
        )
    return PolicyDecisionResponse.model_validate(decision)


@router.get("/customer/{customer_id}", response_model=list[PolicyDecisionResponse])
async def list_policy_decisions_by_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[PolicyDecisionResponse]:
    svc = PolicyService(db)
    decisions = await svc.list_by_customer(customer_id)
    return [PolicyDecisionResponse.model_validate(d) for d in decisions]


@router.get("/payment/{payment_id}", response_model=list[PolicyDecisionResponse])
async def list_policy_decisions_by_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[PolicyDecisionResponse]:
    svc = PolicyService(db)
    decisions = await svc.list_by_payment(payment_id)
    return [PolicyDecisionResponse.model_validate(d) for d in decisions]
