from __future__ import annotations

import random
import string
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.user import User
from app.schemas.simulate import (
    FAILURE_DESCRIPTIONS,
    FAILURE_CODES,
    SimulateCaptureRequest,
    SimulateCaptureResponse,
    SimulateFailureRequest,
    SimulateFailureResponse,
)
from app.services.consent.consent_service import ConsentService
from app.services.customers.customer_service import CustomerService
from app.services.payments.payment_service import PaymentService

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/simulate", tags=["simulate"])


def _generate_razorpay_id(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=14))
    return f"{prefix}_{suffix}"


def _build_webhook_payload(
    order_id: str,
    payment_id: str,
    amount: int,
    currency: str,
    customer_email: str,
    error_code: str,
    error_description: str,
) -> dict[str, Any]:
    return {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": currency,
                    "status": "failed",
                    "method": "upi",
                    "description": "Payment for order",
                    "email": customer_email,
                    "contact": "+919876543210",
                    "error_code": error_code,
                    "error_description": error_description,
                    "created_at": int(uuid.uuid4().time_low) % 10000000000,
                }
            }
        },
    }


async def _process_in_background(
    event: str,
    payload: dict[str, Any],
    raw_payload: dict[str, Any],
) -> None:
    from app.api.webhooks import _process_webhook_event

    await _process_webhook_event(event, payload, raw_payload=raw_payload)


@router.post("/failure", response_model=SimulateFailureResponse)
async def simulate_payment_failure(
    body: SimulateFailureRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> SimulateFailureResponse:
    customer_svc = CustomerService(db)
    payment_svc = PaymentService(db)
    consent_svc = ConsentService(db)

    email = body.customer_email
    name = body.customer_name

    customer = await customer_svc.get_customer_by_email(email)
    if not customer:
        customer = await customer_svc.create_customer(
            email=email,
            name=name,
            phone="+919876543210",
        )

    await consent_svc.opt_in(
        customer_id=customer.id,
        channel="email",
        source="simulate_api",
    )

    razorpay_order_id = _generate_razorpay_id("order")
    razorpay_payment_id = _generate_razorpay_id("pay")

    payment = await payment_svc.create_payment_record(
        order_id=razorpay_order_id,
        amount=body.amount,
        currency="INR",
        customer_email=email,
        customer_phone="+919876543210",
        user_id=current_user.id,
    )

    payment.customer_id = customer.id
    payment.failure_reason = FAILURE_DESCRIPTIONS[body.failure_type]
    await db.flush()

    await db.commit()

    error_description = FAILURE_DESCRIPTIONS[body.failure_type]
    error_code = FAILURE_CODES[body.failure_type]
    raw_payload = _build_webhook_payload(
        order_id=razorpay_order_id,
        payment_id=razorpay_payment_id,
        amount=body.amount,
        currency="INR",
        customer_email=email,
        error_code=error_code,
        error_description=error_description,
    )

    background_tasks.add_task(
        _process_in_background,
        "payment.failed",
        raw_payload.get("payload", {}),
        raw_payload,
    )

    logger.info(
        "payment_failure_simulated",
        extra={
            "customer_id": str(customer.id),
            "payment_id": str(payment.id),
            "order_id": razorpay_order_id,
            "failure_type": body.failure_type.value,
        },
    )

    email_sent_to = settings.TEST_EMAIL if (not settings.is_production and settings.TEST_EMAIL) else email

    return SimulateFailureResponse(
        customer_id=str(customer.id),
        customer_email=email,
        payment_id=str(payment.id),
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        amount=body.amount,
        currency="INR",
        failure_type=body.failure_type.value,
        failure_code=error_code,
        failure_reason=error_description,
        email_sent_to=email_sent_to,
        status="failed",
        recovery_pipeline="queued",
        message=f"Simulated {body.failure_type.value} failure. Customer consented, payment failed, recovery pipeline queued.",
    )


@router.post("/capture", response_model=SimulateCaptureResponse)
async def simulate_payment_capture(
    body: SimulateCaptureRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SimulateCaptureResponse:
    payment_svc = PaymentService(db)
    payment = await payment_svc.get_payment_by_order_id(body.razorpay_order_id)
    if not payment:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Payment not found: {body.razorpay_order_id}")

    previous_status = payment.status
    capture_payment_id = _generate_razorpay_id("pay")

    raw_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": capture_payment_id,
                    "order_id": body.razorpay_order_id,
                    "amount": payment.amount,
                    "currency": payment.currency,
                    "status": "captured",
                    "method": "upi",
                    "description": "Recovery payment captured",
                    "email": payment.customer_email,
                    "contact": "+919876543210",
                    "created_at": int(uuid.uuid4().time_low) % 10000000000,
                }
            }
        },
    }

    background_tasks.add_task(
        _process_in_background,
        "payment.captured",
        raw_payload.get("payload", {}),
        raw_payload,
    )

    logger.info(
        "payment_capture_simulated",
        extra={
            "order_id": body.razorpay_order_id,
            "previous_status": previous_status,
        },
    )

    new_status = "recovered" if previous_status == "recovery_pending" else "captured"

    return SimulateCaptureResponse(
        status="success",
        razorpay_order_id=body.razorpay_order_id,
        previous_status=previous_status,
        new_status=new_status,
        message=f"Simulated payment capture. {previous_status} → {new_status}.",
    )
