

import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import async_session_factory, get_db
from app.schemas.payment import RecoveryStatusResponse, WebhookEventResponse
from app.services.payments.payment_service import PaymentService
from app.services.payments.razorpay_service import razorpay_service
from app.services.recovery.recovery_service import RecoveryService

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["webhooks"])


async def _process_webhook_event(event: str, payload: dict[str, Any]) -> None:
    """Background task to process a verified Razorpay webhook event."""
    async with async_session_factory() as db:
        try:
            payment_svc = PaymentService(db)
            recovery_svc = RecoveryService(db)

            if event == "payment.captured":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                payment_id = entity.get("id")
                if order_id:
                    await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="captured",
                        payment_id=payment_id,
                    )
                    await db.commit()
                    logger.info("webhook_payment_captured", extra={"order_id": order_id})

            elif event == "payment.failed":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                payment_id = entity.get("id")
                if order_id:
                    await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="failed",
                        payment_id=payment_id,
                    )
                    await db.commit()
                    logger.info("webhook_payment_failed", extra={"order_id": order_id})
                    try:
                        await recovery_svc.initiate_recovery(order_id)
                        await db.commit()
                        logger.info("recovery_auto_initiated", extra={"order_id": order_id})
                    except Exception as e:
                        logger.error(
                            "recovery_initiation_failed",
                            extra={"order_id": order_id, "error": str(e)},
                        )

            elif event == "payment.authorized":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                payment_id = entity.get("id")
                if order_id:
                    await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="authorized",
                        payment_id=payment_id,
                    )
                    await db.commit()

            elif event == "payment.refunded":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                if order_id:
                    await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="refunded",
                    )
                    await db.commit()

            else:
                logger.info("unhandled_webhook_event", extra={"event": event})

        except Exception as e:
            await db.rollback()
            logger.error(
                "webhook_processing_error",
                extra={"event": event, "error": str(e)},
            )
            raise


@router.post("/webhooks/razorpay", response_model=WebhookEventResponse)
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(..., alias="X-Razorpay-Signature"),
) -> WebhookEventResponse:
    raw_body = await request.body()

    if not razorpay_service.verify_webhook_signature(
        payload=raw_body, signature=x_razorpay_signature
    ):
        logger.warning("webhook_signature_verification_failed")
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event = data.get("event", "unknown")
    payload = data.get("payload", {})

    logger.info(
        "webhook_received",
        extra={"event": event, "payload_keys": list(payload.keys())},
    )

    background_tasks.add_task(_process_webhook_event, event, payload)

    return WebhookEventResponse(status="received", event=event)


@router.get("/recovery/{payment_id}", response_model=RecoveryStatusResponse)
async def get_recovery_status(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> RecoveryStatusResponse:
    svc = RecoveryService(db)
    status_data = await svc.get_recovery_status(payment_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Payment not found")
    return RecoveryStatusResponse(**status_data)


@router.post("/recovery/retry/{payment_id}")
async def retry_recovery(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = RecoveryService(db)
    try:
        result = await svc.retry_recovery(payment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/webhook-test")
async def webhook_test() -> dict:
    return {
        "status": "ok",
        "message": "Webhook endpoint is live",
        "webhook_url": "https://recoverflow-webhook.share.zrok.io/webhooks/razorpay",
    }


@router.post("/webhook-test")
async def simulate_webhook(request: Request, background_tasks: BackgroundTasks) -> dict:
    """Test endpoint - skips signature verification. Remove before production."""
    raw_body = await request.body()
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = data.get("event", "unknown")
    payload = data.get("payload", {})

    logger.info("test_webhook_received", extra={"event": event})

    background_tasks.add_task(_process_webhook_event, event, payload)

    return {"status": "received", "event": event}
