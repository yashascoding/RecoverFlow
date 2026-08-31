from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.policy import PolicyDecisionCreate, PolicyDecisionResponse
from app.services.policy.policy_service import PolicyService

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("/")
async def list_config_policies():
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "id": "kill-switch",
            "name": "Kill Switch",
            "description": "Master toggle to enable or disable all automated recovery actions",
            "value": False,
            "type": "boolean",
            "unit": None,
            "last_updated": now,
            "updated_by": "system",
        },
        {
            "id": "max-attempts",
            "name": "Max Recovery Attempts",
            "description": "Maximum number of recovery attempts per failed payment",
            "value": 3,
            "type": "number",
            "unit": "attempts",
            "last_updated": now,
            "updated_by": "system",
        },
        {
            "id": "retry-delay",
            "name": "Retry Delay",
            "description": "Time between recovery retry attempts",
            "value": 30,
            "type": "number",
            "unit": "minutes",
            "last_updated": now,
            "updated_by": "system",
        },
        {
            "id": "min-amount",
            "name": "Minimum Recovery Amount",
            "description": "Minimum payment amount to trigger automatic recovery",
            "value": 10000,
            "type": "number",
            "unit": "paise",
            "last_updated": now,
            "updated_by": "system",
        },
        {
            "id": "quiet-hours-start",
            "name": "Quiet Hours Start",
            "description": "Do not send recovery messages after this time",
            "value": "21:00",
            "type": "text",
            "unit": None,
            "last_updated": now,
            "updated_by": "system",
        },
        {
            "id": "quiet-hours-end",
            "name": "Quiet Hours End",
            "description": "Resume sending recovery messages after this time",
            "value": "09:00",
            "type": "text",
            "unit": None,
            "last_updated": now,
            "updated_by": "system",
        },
    ]


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
