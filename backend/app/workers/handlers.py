"""Event handlers — one function per event type.

Each handler receives (event_type, payload_dict) and is run by the worker.
Handlers should be idempotent — the same event may be delivered more than once
during retries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.database import async_session_factory
from app.models.email_message import EmailMessage, EmailStatus

logger = get_logger(__name__)


# ── Payment handlers ──────────────────────────────────────────────────

async def handle_payment_created(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_payment_created",
        extra={"payment_id": payload.get("payment_id"), "order_id": payload.get("razorpay_order_id")},
    )


async def handle_payment_authorized(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_payment_authorized",
        extra={"payment_id": payload.get("payment_id"), "order_id": payload.get("razorpay_order_id")},
    )


async def handle_payment_captured(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_payment_captured",
        extra={"payment_id": payload.get("payment_id"), "order_id": payload.get("razorpay_order_id")},
    )


async def handle_payment_failed(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_payment_failed",
        extra={"payment_id": payload.get("payment_id"), "order_id": payload.get("razorpay_order_id")},
    )


async def handle_payment_refunded(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_payment_refunded",
        extra={"payment_id": payload.get("payment_id"), "order_id": payload.get("razorpay_order_id")},
    )


# ── Email handlers ───────────────────────────────────────────────────

async def handle_email_message_received(event_type: str, payload: dict[str, Any]) -> None:
    logger.info(
        "handler_email_received",
        extra={"message_id": payload.get("message_id"), "customer_id": payload.get("customer_id")},
    )


async def handle_email_message_sent(event_type: str, payload: dict[str, Any]) -> None:
    await _update_email_status(
        payload.get("provider_message_id"),
        EmailStatus.SENT,
        timestamp_field="sent_at",
    )


async def _update_email_status(
    provider_message_id: str | None,
    new_status: EmailStatus,
    timestamp_field: str | None = None,
    error_message: str | None = None,
) -> None:
    """Idempotent helper: find email_messages row and advance status."""
    if not provider_message_id:
        return

    async with async_session_factory() as db:
        result = await db.execute(
            select(EmailMessage).where(
                EmailMessage.provider_message_id == provider_message_id
            )
        )
        email_msg = result.scalar_one_or_none()
        if not email_msg:
            logger.warning(
                "handler_email_status_no_message",
                extra={"provider_message_id": provider_message_id, "target_status": new_status.value},
            )
            return

        now = datetime.now(timezone.utc)
        email_msg.status = new_status.value

        if timestamp_field == "sent_at":
            email_msg.sent_at = now
        elif timestamp_field == "delivered_at":
            email_msg.delivered_at = now
        elif timestamp_field == "opened_at":
            email_msg.opened_at = now
        elif timestamp_field == "failed_at":
            email_msg.failed_at = now

        if error_message:
            email_msg.error_message = error_message

        await db.commit()
        logger.info(
            "handler_email_status_updated",
            extra={
                "provider_message_id": provider_message_id,
                "new_status": new_status.value,
            },
        )


async def handle_email_delivered(event_type: str, payload: dict[str, Any]) -> None:
    await _update_email_status(
        payload.get("provider_message_id"),
        EmailStatus.DELIVERED,
        timestamp_field="delivered_at",
    )


async def handle_email_opened(event_type: str, payload: dict[str, Any]) -> None:
    await _update_email_status(
        payload.get("provider_message_id"),
        EmailStatus.OPENED,
        timestamp_field="opened_at",
    )


async def handle_email_bounced(event_type: str, payload: dict[str, Any]) -> None:
    bounce_reason = payload.get("bounce_reason")
    await _update_email_status(
        payload.get("provider_message_id"),
        EmailStatus.BOUNCED,
        timestamp_field="failed_at",
        error_message=f"Bounce: {bounce_reason}" if bounce_reason else "Bounced",
    )


async def handle_email_complained(event_type: str, payload: dict[str, Any]) -> None:
    await _update_email_status(
        payload.get("provider_message_id"),
        EmailStatus.FAILED,
        timestamp_field="failed_at",
        error_message="Spam complaint",
    )


# ── Registry ────────────────────────────────────────────────────────────────

HANDLERS: dict[str, Any] = {
    "payment.created": handle_payment_created,
    "payment.authorized": handle_payment_authorized,
    "payment.captured": handle_payment_captured,
    "payment.failed": handle_payment_failed,
    "payment.refunded": handle_payment_refunded,
    "email.message.received": handle_email_message_received,
    "email.message.sent": handle_email_message_sent,
    "email.delivered": handle_email_delivered,
    "email.opened": handle_email_opened,
    "email.bounced": handle_email_bounced,
    "email.complained": handle_email_complained,
}
