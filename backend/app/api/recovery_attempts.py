from __future__ import annotations

import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.recovery_attempt import RecoveryAttempt
from app.schemas.recovery_attempt import (
    RecoveryAttemptCreate,
    RecoveryAttemptResponse,
    RecoveryAttemptStatusUpdate,
)
from app.services.recovery.recovery_attempt_service import RecoveryAttemptService

router = APIRouter(prefix="/recovery-attempts", tags=["recovery-attempts"])


@router.get("/")
async def list_all_recovery_attempts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    count_q = select(func.count()).select_from(RecoveryAttempt)
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    query = select(RecoveryAttempt).order_by(RecoveryAttempt.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    from app.models.payment import Payment
    payment_ids = [a.payment_id for a in items]
    if payment_ids:
        payments_result = await db.execute(
            select(Payment).where(Payment.id.in_(payment_ids))
        )
        payments_map = {str(p.id): p for p in payments_result.scalars().all()}
    else:
        payments_map = {}

    enriched = []
    for a in items:
        p = payments_map.get(str(a.payment_id))
        enriched.append({
            "id": str(a.id),
            "payment_id": str(a.payment_id),
            "payment_order_id": p.razorpay_order_id if p else "",
            "customer_name": p.customer_email.split("@")[0] if p else "",
            "customer_email": p.customer_email if p else "",
            "original_amount": p.amount if p else a.amount,
            "recovery_amount": a.amount if a.status in ("converted",) else None,
            "recovery_time": a.converted_at.isoformat() if a.converted_at else None,
            "channel": a.channel,
            "status": a.status,
            "agent_run_id": None,
            "created_at": a.created_at.isoformat(),
            "sent_at": a.sent_at.isoformat() if a.sent_at else None,
            "opened_at": a.opened_at.isoformat() if a.opened_at else None,
            "recovered_at": a.converted_at.isoformat() if a.converted_at else None,
        })
    return enriched


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
