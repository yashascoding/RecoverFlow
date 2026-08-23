from __future__ import annotations

import resend

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

resend.api_key = settings.RESEND_API_KEY

FROM_EMAIL = "onboarding@resend.dev"


def send_recovery_email(
    to_email: str,
    customer_name: str,
    payment_id: str,
) -> dict:
    response = resend.Emails.send({
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": "Your payment needs your attention",
        "html": f"""
        <h2>Hi {customer_name},</h2>

        <p>We noticed that your recent payment could not be completed.</p>

        <p>
            Please try your payment again to complete your order.
        </p>

        <p>Payment ID: {payment_id}</p>

        <p>Thanks,<br>RecoverFlow</p>
        """
    })

    logger.info(
        "recovery_email_sent",
        extra={"to": to_email, "payment_id": payment_id, "provider_message_id": response.get("id")},
    )

    return response
