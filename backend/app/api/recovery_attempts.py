from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.recovery_attempt import (
    RecoveryAttemptCreate,
    RecoveryAttemptResponse,
    RecoveryAttemptStatusUpdate,
)
from app.services.recovery.recovery_attempt_service import RecoveryAttemptService

router = APIRouter(prefix="/recovery-attempts", tags=["recovery-attempts"])


@router.post("/", response_model=RecoveryAttemptResponse, status_code=status.HTTP_201_CREATED)
async def create_recovery_attempt(
    body: RecoveryAttemptCreate,
    db: AsyncSession = Depends(get_db),
) -> RecoveryAttemptResponse:
    svc = RecoveryAttemptService(db)
    attempt = await svc.create(
        customer_id=body.customer_id,
        payment_id=body.payment_id,
        channel=body.channel.value,
        amount=body.amount,
    )
    await db.commit()
    return RecoveryAttemptResponse.model_validate(attempt)


@router.get("/{attempt_id}", response_model=RecoveryAttemptResponse)
async def get_recovery_attempt(
    attempt_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecoveryAttemptResponse:
    svc = RecoveryAttemptService(db)
    attempt = await svc.get_by_id(attempt_id)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery attempt not found",
        )
    return RecoveryAttemptResponse.model_validate(attempt)


@router.get("/payment/{payment_id}", response_model=list[RecoveryAttemptResponse])
async def list_recovery_attempts_by_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[RecoveryAttemptResponse]:
    svc = RecoveryAttemptService(db)
    attempts = await svc.list_by_payment(payment_id)
    return [RecoveryAttemptResponse.model_validate(a) for a in attempts]


@router.patch("/{attempt_id}/status", response_model=RecoveryAttemptResponse)
async def update_recovery_attempt_status(
    attempt_id: uuid.UUID,
    body: RecoveryAttemptStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> RecoveryAttemptResponse:
    svc = RecoveryAttemptService(db)
    attempt = await svc.update_status(attempt_id, body.status)
    if not attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery attempt not found",
        )
    await db.commit()
    return RecoveryAttemptResponse.model_validate(attempt)
