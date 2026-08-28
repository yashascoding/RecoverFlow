from __future__ import annotations

import asyncio
import enum
from dataclasses import dataclass

import resend

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

resend.api_key = settings.RESEND_API_KEY

DEFAULT_FROM_EMAIL = "onboarding@resend.dev"

# Resend API errors that are safe to retry (transient)
_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds


class EmailSendErrorCategory(str, enum.Enum):
    """Classifies email send failures for upstream handling."""

    INVALID_RECIPIENT = "invalid_recipient"
    RATE_LIMITED = "rate_limited"
    PROVIDER_ERROR = "provider_error"
    AUTH_ERROR = "auth_error"
    UNKNOWN = "unknown"


@dataclass
class EmailSendResult:
    """Structured result from an email send attempt."""

    success: bool
    provider_message_id: str | None = None
    error_category: EmailSendErrorCategory | None = None
    error_message: str | None = None
    status_code: int | None = None

    @property
    def is_retryable(self) -> bool:
        return self.error_category in (
            EmailSendErrorCategory.RATE_LIMITED,
            EmailSendErrorCategory.PROVIDER_ERROR,
        )


def _classify_error(exc: Exception) -> EmailSendErrorCategory:
    """Map a Resend API exception to a failure category."""
    msg = str(exc).lower()

    if "invalid" in msg and ("email" in msg or "recipient" in msg or "address" in msg):
        return EmailSendErrorCategory.INVALID_RECIPIENT
    if "rate" in msg or "limit" in msg or "429" in msg:
        return EmailSendErrorCategory.RATE_LIMITED
    if "unauthorized" in msg or "forbidden" in msg or "api_key" in msg or "401" in msg or "403" in msg:
        return EmailSendErrorCategory.AUTH_ERROR
    return EmailSendErrorCategory.PROVIDER_ERROR


class ResendEmailService:
    """Sends emails via the Resend API with retry and structured error handling."""

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        from_email: str | None = None,
    ) -> EmailSendResult:
        """Send a single email. Returns a structured result."""
        sender = from_email or settings.RECOVERY_EMAIL_FROM or DEFAULT_FROM_EMAIL

        last_error: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = resend.Emails.send({
                    "from": sender,
                    "to": [to],
                    "subject": subject,
                    "html": body,
                })

                provider_id = response.get("id") if isinstance(response, dict) else None
                logger.info(
                    "email_sent",
                    extra={
                        "to": to,
                        "subject": subject,
                        "provider_message_id": provider_id,
                        "attempt": attempt,
                    },
                )
                return EmailSendResult(
                    success=True,
                    provider_message_id=provider_id,
                )

            except Exception as exc:
                last_error = exc
                category = _classify_error(exc)
                status_code = getattr(exc, "status_code", None)

                logger.warning(
                    "email_send_attempt_failed",
                    extra={
                        "to": to,
                        "attempt": attempt,
                        "error_category": category.value,
                        "error": str(exc),
                        "status_code": status_code,
                    },
                )

                # Don't retry auth or recipient errors — they won't self-heal
                if category in (
                    EmailSendErrorCategory.AUTH_ERROR,
                    EmailSendErrorCategory.INVALID_RECIPIENT,
                ):
                    return EmailSendResult(
                        success=False,
                        error_category=category,
                        error_message=str(exc),
                        status_code=status_code,
                    )

                # Retryable: wait with exponential backoff
                if attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        # All retries exhausted
        category = _classify_error(last_error) if last_error else EmailSendErrorCategory.UNKNOWN
        return EmailSendResult(
            success=False,
            error_category=category,
            error_message=str(last_error) if last_error else "Unknown error after retries",
            status_code=getattr(last_error, "status_code", None),
        )
