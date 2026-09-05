from __future__ import annotations

import hashlib
import hmac
from typing import Any

import razorpay
from razorpay.errors import BadRequestError, ServerError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RazorpayService:
    def __init__(self) -> None:
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_payment_link(
        self,
        amount: int,
        currency: str,
        customer_email: str,
        description: str = "Payment for your order",
    ) -> dict[str, Any]:
        """Create a Razorpay payment link."""
        try:
            payload = {
                "amount": amount,
                "currency": currency,
                "description": description,
                "customer": {"email": customer_email},
                "notify": {"email": False},
                "reminder_enable": True,
            }
            response = self.client.payment_link.create(payload)
            logger.info(
                "payment_link_created",
                extra={"amount": amount, "currency": currency},
            )
            return response
        except BadRequestError as e:
            logger.error("razorpay_bad_request", extra={"error": str(e)})
            raise
        except ServerError as e:
            logger.error("razorpay_server_error", extra={"error": str(e)})
            raise

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str | None = None,
    ) -> bool:
        """Verify Razorpay webhook signature using HMAC-SHA256."""
        secret = secret or settings.RAZORPAY_WEBHOOK_SECRET
        try:
            expected = hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()
            result = hmac.compare_digest(expected, signature)
            if not result:
                logger.warning(
                    "webhook_signature_mismatch",
                    extra={
                        "received_sig_length": len(signature) if signature else 0,
                        "expected_sig_length": len(expected),
                        "secret_length": len(secret),
                        "payload_length": len(payload),
                    },
                )
            return result
        except Exception as e:
            logger.error("webhook_verification_error", extra={"error": str(e)})
            return False

    def get_payment_details(self, payment_id: str) -> dict[str, Any]:
        """Fetch payment details from Razorpay."""
        try:
            response = self.client.payment.fetch(payment_id)
            logger.info("payment_fetched", extra={"payment_id": payment_id})
            return response
        except BadRequestError as e:
            logger.error(
                "razorpay_fetch_bad_request",
                extra={"payment_id": payment_id, "error": str(e)},
            )
            raise
        except ServerError as e:
            logger.error(
                "razorpay_fetch_server_error",
                extra={"payment_id": payment_id, "error": str(e)},
            )
            raise

    def capture_payment(self, payment_id: str, amount: int) -> dict[str, Any]:
        """Capture a Razorpay payment."""
        try:
            response = self.client.payment.capture(payment_id, amount)
            logger.info(
                "payment_captured",
                extra={"payment_id": payment_id, "amount": amount},
            )
            return response
        except BadRequestError as e:
            logger.error(
                "razorpay_capture_bad_request",
                extra={"payment_id": payment_id, "error": str(e)},
            )
            raise
        except ServerError as e:
            logger.error(
                "razorpay_capture_server_error",
                extra={"payment_id": payment_id, "error": str(e)},
            )
            raise

    def create_order(
        self, amount: int, currency: str, receipt: str | None = None
    ) -> dict[str, Any]:
        """Create a Razorpay order."""
        try:
            payload: dict[str, Any] = {
                "amount": amount,
                "currency": currency,
            }
            if receipt:
                payload["receipt"] = receipt
            response = self.client.order.create(payload)
            logger.info(
                "order_created",
                extra={"order_id": response.get("id"), "amount": amount},
            )
            return response
        except BadRequestError as e:
            logger.error("razorpay_order_bad_request", extra={"error": str(e)})
            raise
        except ServerError as e:
            logger.error("razorpay_order_server_error", extra={"error": str(e)})
            raise


razorpay_service = RazorpayService()
