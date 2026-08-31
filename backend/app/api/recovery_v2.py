from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.payment import Payment
from app.schemas.customer import CustomerResponse
from app.schemas.payment import PaymentResponse
from app.services.recovery.failure_diagnosis import FailureDiagnosisEngine
from app.services.recovery.recovery_service_v2 import (
    CustomerNotFoundError,
    DuplicateRecoveryLinkError,
    InvalidPaymentStateError,
    PaymentNotFoundError,
    RecoveryServiceV2,
)

router = APIRouter(prefix="/recovery/v2", tags=["recovery-v2"])


# ── Schemas ──────────────────────────────────────────────────────────────
class DiagnoseRequest(BaseModel):
    failure_reason: str | None = None


class DiagnoseResponse(BaseModel):
    category: str
    strategy: str
    reason: str
    retry_after_seconds: int | None = None
    max_retries: int | None = None
    context: dict = Field(default_factory=dict)


class PaymentHistoryResponse(BaseModel):
    items: list[PaymentResponse]
    total: int


class PaymentLinkRequest(BaseModel):
    amount_override: int | None = Field(default=None, gt=0)
    expiry_hours: int = Field(default=48, ge=1, le=168)


class PaymentLinkResponse(BaseModel):
    link_id: str
    url: str
    amount: int
    created_at: str
    expires_at: str
    payment_id: str


# ── Failure Diagnosis ────────────────────────────────────────────────────
@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose_failure(body: DiagnoseRequest) -> DiagnoseResponse:
    engine = FailureDiagnosisEngine()
    result = engine.diagnose(body.failure_reason)
    return DiagnoseResponse(**result.to_dict())


# ── Customer ─────────────────────────────────────────────────────────────
@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    svc = RecoveryServiceV2(db)
    try:
        customer = await svc.get_customer(customer_id)
    except CustomerNotFoundError:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse.model_validate(customer)


@router.get("/customers/by-email/{email}", response_model=CustomerResponse)
async def get_customer_by_email(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    svc = RecoveryServiceV2(db)
    try:
        customer = await svc.get_customer_by_email(email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CustomerNotFoundError:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerResponse.model_validate(customer)


# ── Payment ──────────────────────────────────────────────────────────────
@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    svc = RecoveryServiceV2(db)
    try:
        payment = await svc.get_payment(payment_id)
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")
    return PaymentResponse.model_validate(payment)


@router.get(
    "/payments/{payment_id}/validate/{state}",
    response_model=PaymentResponse,
)
async def get_payment_in_state(
    payment_id: uuid.UUID,
    state: str,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    svc = RecoveryServiceV2(db)
    try:
        payment = await svc.get_payment_in_state(payment_id, state)
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")
    except InvalidPaymentStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return PaymentResponse.model_validate(payment)


# ── Payment History ──────────────────────────────────────────────────────
@router.get(
    "/customers/{customer_id}/payments",
    response_model=PaymentHistoryResponse,
)
async def get_payment_history(
    customer_id: uuid.UUID,
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> PaymentHistoryResponse:
    svc = RecoveryServiceV2(db)
    try:
        await svc.get_customer(customer_id)
    except CustomerNotFoundError:
        raise HTTPException(status_code=404, detail="Customer not found")

    items = await svc.get_payment_history(
        customer_id, status=status, limit=limit, offset=offset
    )
    total = await svc.get_payment_history_count(customer_id, status=status)
    return PaymentHistoryResponse(
        items=[PaymentResponse.model_validate(p) for p in items],
        total=total,
    )


# ── Create Payment Link ─────────────────────────────────────────────────
@router.post(
    "/payments/{payment_id}/link",
    response_model=PaymentLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_payment_link(
    payment_id: uuid.UUID,
    body: PaymentLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> PaymentLinkResponse:
    svc = RecoveryServiceV2(db)
    try:
        link = await svc.create_payment_link(
            payment_id,
            amount_override=body.amount_override,
            expiry_hours=body.expiry_hours,
        )
    except PaymentNotFoundError:
        raise HTTPException(status_code=404, detail="Payment not found")
    except InvalidPaymentStateError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except DuplicateRecoveryLinkError:
        raise HTTPException(
            status_code=409, detail="Recovery link already exists for this payment"
        )
    return PaymentLinkResponse(**link)


# ── Incidents ────────────────────────────────────────────────────────────
@router.get("/incidents")
async def list_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Payment)
        .where(Payment.status.in_(["failed", "recovery_pending"]))
        .order_by(Payment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "payment_id": str(p.id),
            "payment_order_id": p.razorpay_order_id,
            "customer_name": p.customer_email.split("@")[0],
            "customer_email": p.customer_email,
            "amount": p.amount,
            "failure_reason": p.failure_reason or "Unknown failure",
            "severity": "high" if p.amount >= 10000 else "medium" if p.amount >= 1000 else "low",
            "status": "new" if p.status == "failed" else "investigating",
            "recovery_state": p.status,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in payments
    ]
