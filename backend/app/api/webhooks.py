import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.webhook import verify_svix_signature, WebhookVerificationError
from app.db.database import async_session_factory, get_db
from app.events.dispatcher import event_bus
from app.models.email_message import EmailMessage, EmailStatus
from app.schemas.event import (
    EventSource,
    PaymentAuthorizedEvent,
    PaymentCapturedEvent,
    PaymentFailedEvent,
    PaymentRefundedEvent,
    PaymentEventPayload,
    EmailEventPayload,
    EmailDeliveredEvent,
    EmailOpenedEvent,
    EmailBouncedEvent,
    EmailComplainedEvent,
)
from app.schemas.payment import RecoveryStatusResponse, WebhookEventResponse
from app.services.payments.payment_service import PaymentService
from app.services.payments.razorpay_service import razorpay_service
from app.services.recovery.recovery_service import RecoveryService

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(tags=["webhooks"])


# ---------------------------------------------------------------------------
# Resend webhook event → internal event mapping
# ---------------------------------------------------------------------------
RESEND_EVENT_MAP: dict[str, str] = {
    "email.sent": "email.message.sent",
    "email.delivered": "email.delivered",
    "email.opened": "email.opened",
    "email.bounced": "email.bounced",
    "email.complained": "email.complained",
}


# ---------------------------------------------------------------------------
# Razorpay — background processor
# ---------------------------------------------------------------------------
async def _process_webhook_event(
    event: str,
    payload: dict[str, Any],
    raw_payload: dict[str, Any] | None = None,
) -> None:
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
                    payment = await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="captured",
                        payment_id=payment_id,
                    )
                    await db.commit()
                    logger.info("webhook_payment_captured", extra={"order_id": order_id})

                    if payment:
                        await event_bus.dispatch(
                            PaymentCapturedEvent(
                                source=EventSource.WEBHOOK,
                                payload=PaymentEventPayload(
                                    payment_id=payment.id,
                                    razorpay_order_id=payment.razorpay_order_id,
                                    razorpay_payment_id=payment.razorpay_payment_id,
                                    customer_id=payment.customer_id,
                                    customer_email=payment.customer_email,
                                    amount=payment.amount,
                                    currency=payment.currency,
                                    status=payment.status,
                                ),
                            ),
                            raw_payload=raw_payload,
                        )

            elif event == "payment.failed":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                payment_id = entity.get("id")
                if order_id:
                    payment = await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="failed",
                        payment_id=payment_id,
                    )
                    await db.commit()
                    logger.info("webhook_payment_failed", extra={"order_id": order_id})

                    if payment:
                        await event_bus.dispatch(
                            PaymentFailedEvent(
                                source=EventSource.WEBHOOK,
                                payload=PaymentEventPayload(
                                    payment_id=payment.id,
                                    razorpay_order_id=payment.razorpay_order_id,
                                    razorpay_payment_id=payment.razorpay_payment_id,
                                    customer_id=payment.customer_id,
                                    customer_email=payment.customer_email,
                                    amount=payment.amount,
                                    currency=payment.currency,
                                    status=payment.status,
                                ),
                                failure_reason=entity.get("error_description"),
                            ),
                            raw_payload=raw_payload,
                        )

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
                    payment = await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="authorized",
                        payment_id=payment_id,
                    )
                    await db.commit()

                    if payment:
                        await event_bus.dispatch(
                            PaymentAuthorizedEvent(
                                source=EventSource.WEBHOOK,
                                payload=PaymentEventPayload(
                                    payment_id=payment.id,
                                    razorpay_order_id=payment.razorpay_order_id,
                                    razorpay_payment_id=payment.razorpay_payment_id,
                                    customer_id=payment.customer_id,
                                    customer_email=payment.customer_email,
                                    amount=payment.amount,
                                    currency=payment.currency,
                                    status=payment.status,
                                ),
                            ),
                            raw_payload=raw_payload,
                        )

            elif event == "payment.refunded":
                entity = payload.get("payment", {}).get("entity", {})
                order_id = entity.get("order_id")
                if order_id:
                    payment = await payment_svc.update_payment_status(
                        order_id=order_id,
                        status="refunded",
                    )
                    await db.commit()

                    if payment:
                        await event_bus.dispatch(
                            PaymentRefundedEvent(
                                source=EventSource.WEBHOOK,
                                payload=PaymentEventPayload(
                                    payment_id=payment.id,
                                    razorpay_order_id=payment.razorpay_order_id,
                                    razorpay_payment_id=payment.razorpay_payment_id,
                                    customer_id=payment.customer_id,
                                    customer_email=payment.customer_email,
                                    amount=payment.amount,
                                    currency=payment.currency,
                                    status=payment.status,
                                ),
                            ),
                            raw_payload=raw_payload,
                        )

            else:
                logger.info("unhandled_webhook_event", extra={"event": event})

        except Exception as e:
            await db.rollback()
            logger.error(
                "webhook_processing_error",
                extra={"event": event, "error": str(e)},
            )


# ---------------------------------------------------------------------------
# Resend — background processor
# ---------------------------------------------------------------------------
async def _process_resend_event(
    resend_event: str,
    data: dict[str, Any],
    raw_payload: dict[str, Any] | None = None,
) -> None:
    """Process a verified Resend webhook event in the background."""
    async with async_session_factory() as db:
        try:
            provider_message_id = data.get("email_id") or data.get("message_id")
            created_at = data.get("created_at")
            from_email = data.get("from", "")
            to_list = data.get("to", [])
            to_email = to_list[0] if isinstance(to_list, list) and to_list else ""
            subject = data.get("subject")
            bounce_type = data.get("bounce")  # present on email.bounced

            # ── find the email_messages row by provider_message_id (idempotent) ──
            email_msg: EmailMessage | None = None
            if provider_message_id:
                result = await db.execute(
                    select(EmailMessage).where(
                        EmailMessage.provider_message_id == provider_message_id
                    )
                )
                email_msg = result.scalar_one_or_none()

            now_iso = None
            if created_at:
                from datetime import datetime, timezone
                try:
                    now_iso = datetime.fromtimestamp(created_at, tz=timezone.utc)
                except (TypeError, ValueError, OSError):
                    now_iso = None

            # ── update email_messages table (idempotent: only advance status) ──
            if email_msg:
                status_updated = False

                if resend_event == "email.sent" and email_msg.status in (
                    EmailStatus.PENDING.value, EmailStatus.QUEUED.value,
                ):
                    email_msg.status = EmailStatus.SENT.value
                    email_msg.sent_at = now_iso or email_msg.sent_at
                    status_updated = True

                elif resend_event == "email.delivered" and email_msg.status in (
                    EmailStatus.PENDING.value, EmailStatus.QUEUED.value, EmailStatus.SENT.value,
                ):
                    email_msg.status = EmailStatus.DELIVERED.value
                    email_msg.delivered_at = now_iso or email_msg.delivered_at
                    status_updated = True

                elif resend_event == "email.opened" and email_msg.status in (
                    EmailStatus.PENDING.value, EmailStatus.QUEUED.value, EmailStatus.SENT.value, EmailStatus.DELIVERED.value,
                ):
                    email_msg.status = EmailStatus.OPENED.value
                    email_msg.opened_at = now_iso or email_msg.opened_at
                    status_updated = True

                elif resend_event == "email.bounced":
                    email_msg.status = EmailStatus.BOUNCED.value
                    email_msg.failed_at = now_iso or email_msg.failed_at
                    email_msg.error_message = (
                        f"Bounce type: {bounce_type}" if bounce_type else "Bounced"
                    )
                    status_updated = True

                elif resend_event == "email.complained":
                    email_msg.status = EmailStatus.FAILED.value
                    email_msg.failed_at = now_iso or email_msg.failed_at
                    email_msg.error_message = "Spam complaint"
                    status_updated = True

                if status_updated:
                    await db.commit()
                    logger.info(
                        "resend_email_status_updated",
                        extra={
                            "provider_message_id": provider_message_id,
                            "new_status": email_msg.status,
                            "resend_event": resend_event,
                        },
                    )
            else:
                logger.warning(
                    "resend_event_no_email_message_found",
                    extra={
                        "provider_message_id": provider_message_id,
                        "resend_event": resend_event,
                        "to_email": to_email,
                    },
                )

            # ── dispatch internal event to event bus ──
            if resend_event == "email.delivered" and email_msg:
                await event_bus.dispatch(
                    EmailDeliveredEvent(
                        source=EventSource.WEBHOOK,
                        payload=EmailEventPayload(
                            message_id=email_msg.id,
                            customer_id=email_msg.customer_id,
                            recipient_email=email_msg.recipient_email,
                            template_id=email_msg.template_id,
                            subject=email_msg.subject,
                            provider_message_id=provider_message_id,
                        ),
                    ),
                    raw_payload=raw_payload,
                )

            elif resend_event == "email.opened" and email_msg:
                await event_bus.dispatch(
                    EmailOpenedEvent(
                        source=EventSource.WEBHOOK,
                        payload=EmailEventPayload(
                            message_id=email_msg.id,
                            customer_id=email_msg.customer_id,
                            recipient_email=email_msg.recipient_email,
                            template_id=email_msg.template_id,
                            subject=email_msg.subject,
                            provider_message_id=provider_message_id,
                        ),
                    ),
                    raw_payload=raw_payload,
                )

            elif resend_event == "email.bounced" and email_msg:
                await event_bus.dispatch(
                    EmailBouncedEvent(
                        source=EventSource.WEBHOOK,
                        payload=EmailEventPayload(
                            message_id=email_msg.id,
                            customer_id=email_msg.customer_id,
                            recipient_email=email_msg.recipient_email,
                            template_id=email_msg.template_id,
                            subject=email_msg.subject,
                            provider_message_id=provider_message_id,
                        ),
                        bounce_reason=str(bounce_type) if bounce_type else None,
                    ),
                    raw_payload=raw_payload,
                )

            elif resend_event == "email.complained" and email_msg:
                await event_bus.dispatch(
                    EmailComplainedEvent(
                        source=EventSource.WEBHOOK,
                        payload=EmailEventPayload(
                            message_id=email_msg.id,
                            customer_id=email_msg.customer_id,
                            recipient_email=email_msg.recipient_email,
                            template_id=email_msg.template_id,
                            subject=email_msg.subject,
                            provider_message_id=provider_message_id,
                        ),
                    ),
                    raw_payload=raw_payload,
                )

            elif resend_event == "email.sent" and email_msg:
                # email.message.sent already dispatched when we send via Resend API
                pass

        except Exception as e:
            await db.rollback()
            logger.error(
                "resend_webhook_processing_error",
                extra={"resend_event": resend_event, "error": str(e)},
            )


# ---------------------------------------------------------------------------
# Razorpay webhook endpoint
# ---------------------------------------------------------------------------
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

    background_tasks.add_task(_process_webhook_event, event, payload, raw_payload=data)

    return WebhookEventResponse(status="received", event=event)


# ---------------------------------------------------------------------------
# Resend webhook endpoint
# ---------------------------------------------------------------------------
@router.post("/webhooks/resend", response_model=WebhookEventResponse)
async def resend_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    svix_id: str = Header(..., alias="svix-id"),
    svix_timestamp: str = Header(..., alias="svix-timestamp"),
    svix_signature: str = Header(..., alias="svix-signature"),
) -> WebhookEventResponse:
    """Receive and verify Resend email webhooks.

    Uses Svix HMAC-SHA256 signature verification.
    Returns 200 immediately; processing happens in background.
    """
    raw_body = await request.body()

    # 1. Verify Svix signature
    try:
        verify_svix_signature(
            raw_body=raw_body,
            svix_id=svix_id,
            svix_timestamp=svix_timestamp,
            svix_signature=svix_signature,
            webhook_secret=settings.RESEND_WEBHOOK_SECRET,
        )
    except WebhookVerificationError as e:
        logger.warning(
            "resend_webhook_signature_verification_failed",
            extra={"error": str(e)},
        )
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 2. Parse JSON
    try:
        data = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    resend_event = data.get("type", "")
    event_data = data.get("data", {})

    logger.info(
        "resend_webhook_received",
        extra={
            "resend_event": resend_event,
            "email_id": event_data.get("email_id"),
            "to": event_data.get("to"),
        },
    )

    # 3. Validate event type
    if resend_event not in RESEND_EVENT_MAP:
        logger.info(
            "resend_webhook_unhandled_event",
            extra={"resend_event": resend_event},
        )
        return WebhookEventResponse(status="received", event=resend_event)

    # 4. Process in background
    background_tasks.add_task(_process_resend_event, resend_event, event_data, raw_payload=data)

    return WebhookEventResponse(status="received", event=resend_event)


# ---------------------------------------------------------------------------
# Recovery endpoints
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Test endpoints
# ---------------------------------------------------------------------------
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

    background_tasks.add_task(_process_webhook_event, event, payload, raw_payload=data)

    return {"status": "received", "event": event}
