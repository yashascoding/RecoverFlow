from __future__ import annotations

import uuid
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.payment import (
    PaymentCreate,
    PaymentListResponse,
    PaymentResponse,
    PaymentStatusUpdate,
)
from app.services.payments.payment_service import PaymentService
from app.services.payments.payment_transition_service import (
    InvalidTransitionError,
    PaymentTransitionService,
)
from app.services.payments.razorpay_service import razorpay_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    body: PaymentCreate,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    try:
        order = razorpay_service.create_order(
            amount=body.amount,
            currency=body.currency,
            receipt=f"rcpt_{uuid.uuid4().hex[:12]}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Razorpay order creation failed: {e}",
        )

    svc = PaymentService(db)
    payment = await svc.create_payment_record(
        order_id=order["id"],
        amount=body.amount,
        currency=body.currency,
        customer_email=body.customer_email,
        customer_phone=body.customer_phone,
    )

    return PaymentResponse.model_validate(payment)


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    svc = PaymentService(db)
    payment = await svc.get_payment_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return PaymentResponse.model_validate(payment)


@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    status_filter: str | None = Query(None, alias="status"),
    customer_email: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    from app.models.payment import PaymentStatus

    ps: PaymentStatus | None = None
    if status_filter:
        try:
            ps = PaymentStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            )

    svc = PaymentService(db)
    items, total = await svc.list_payments(
        status=ps, customer_email=customer_email, page=page, page_size=page_size
    )

    return PaymentListResponse(
        items=[PaymentResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


@router.patch("/{payment_id}/status", response_model=PaymentResponse)
async def update_payment_status(
    payment_id: uuid.UUID,
    body: PaymentStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    svc = PaymentTransitionService(db)
    try:
        payment = await svc.transition(
            payment_id=str(payment_id),
            target_status=body.status.value,
            failure_reason=body.failure_reason,
        )
    except InvalidTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    await db.commit()
    return PaymentResponse.model_validate(payment)
