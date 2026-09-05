from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.payment import Payment
from app.models.user import User
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
    current_user: Annotated[User, Depends(get_current_user)],
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
        user_id=current_user.id,
    )

    return PaymentResponse.model_validate(payment)


@router.get("/stats/overview")
async def get_overview_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    sixty_days_ago = datetime.now(timezone.utc) - timedelta(days=60)

    all_query = select(Payment).where(Payment.user_id == current_user.id)
    current_query = select(Payment).where(Payment.user_id == current_user.id, Payment.created_at >= thirty_days_ago)
    previous_query = select(Payment).where(
        Payment.user_id == current_user.id, Payment.created_at >= sixty_days_ago, Payment.created_at < thirty_days_ago
    )

    all_result = await db.execute(all_query)
    all_payments = list(all_result.scalars().all())

    current_result = await db.execute(current_query)
    current_payments = list(current_result.scalars().all())

    previous_result = await db.execute(previous_query)
    previous_payments = list(previous_result.scalars().all())

    def calc_metrics(payments):
        total_revenue = sum(p.amount for p in payments if p.status in ("captured", "recovered"))
        failed = [p for p in payments if p.status == "failed" or p.status == "recovery_pending"]
        recovered = [p for p in payments if p.status == "recovered"]
        revenue_at_risk = sum(p.amount for p in failed)
        recovered_revenue = sum(p.amount for p in recovered)
        total = len(payments)
        recovery_rate = round((len(recovered) / len(failed) * 100), 1) if failed else 0
        return {
            "total_revenue": total_revenue,
            "revenue_at_risk": revenue_at_risk,
            "recovered_revenue": recovered_revenue,
            "failed_payments": len(failed),
            "recovery_rate": recovery_rate,
            "total_payments": total,
        }

    current = calc_metrics(current_payments)
    previous = calc_metrics(previous_payments)

    return {
        "total_revenue": current["total_revenue"],
        "revenue_at_risk": current["revenue_at_risk"],
        "recovered_revenue": current["recovered_revenue"],
        "failed_payments": current["failed_payments"],
        "recovery_rate": current["recovery_rate"],
        "total_payments": current["total_payments"],
        "previous_period_revenue": previous["total_revenue"],
        "previous_period_recovered": previous["recovered_revenue"],
        "previous_period_failed": previous["failed_payments"],
    }


@router.get("/recent-activity")
async def get_recent_activity(
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    query = select(Payment).where(Payment.user_id == current_user.id).order_by(Payment.created_at.desc()).limit(limit)
    result = await db.execute(query)
    payments = result.scalars().all()
    return [
        {
            "id": str(p.razorpay_order_id),
            "customer": p.customer_email.split("@")[0],
            "amount": p.amount,
            "status": p.status,
            "time": p.created_at.isoformat(),
        }
        for p in payments
    ]


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> PaymentResponse:
    svc = PaymentService(db)
    payment = await svc.get_payment_by_id(payment_id, user_id=current_user.id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return PaymentResponse.model_validate(payment)


@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    current_user: Annotated[User, Depends(get_current_user)],
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
        status=ps, customer_email=customer_email, user_id=current_user.id, page=page, page_size=page_size
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


@router.post("/{payment_id}/check-recovery")
async def check_recovery_status(
    payment_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Manually check Razorpay for payment status — fallback when webhooks fail."""
    from app.core.logging import get_logger
    from app.models.payment import PaymentStatus

    logger = get_logger(__name__)
    svc = PaymentService(db)
    payment = await svc.get_payment_by_id(payment_id, user_id=current_user.id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status not in ("recovery_pending", "failed"):
        return {"status": payment.status, "message": "Payment is not in a recoverable state"}

    # Try to find the payment_link_id from metadata
    pl_id = (payment.metadata_ or {}).get("razorpay_payment_link_id")

    result = {"payment_id": str(payment.id), "checked_at": datetime.now(timezone.utc).isoformat()}

    if pl_id:
        try:
            pl_details = razorpay_service.client.payment_link.fetch(pl_id)
            pl_status = pl_details.get("status")
            result["payment_link_status"] = pl_status
            logger.info("payment_link_fetched", extra={"payment_link_id": pl_id, "status": pl_status})

            if pl_status == "paid":
                # Find the payment_id from the payment link
                payments_list = pl_details.get("payments", [])
                if payments_list:
                    razorpay_pay_id = payments_list[0].get("id")
                    if razorpay_pay_id:
                        payment.razorpay_payment_id = razorpay_pay_id

                transition_svc = PaymentTransitionService(db)
                payment = await transition_svc.record_recovery_success(payment.razorpay_order_id)
                await db.commit()
                result["new_status"] = "recovered"
                result["message"] = "Payment recovered successfully!"
                logger.info("manual_recovery_confirmed", extra={"payment_id": str(payment.id), "payment_link_id": pl_id})
            else:
                result["new_status"] = payment.status
                result["message"] = f"Payment link status: {pl_status}"
        except Exception as e:
            logger.warning("payment_link_fetch_failed", extra={"payment_link_id": pl_id, "error": str(e)})
            result["error"] = str(e)
            result["message"] = "Could not fetch payment link status from Razorpay"
    else:
        result["message"] = "No payment link ID found in metadata — cannot check Razorpay status"
        result["new_status"] = payment.status

    return result
