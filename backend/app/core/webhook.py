"""Svix-compatible webhook signature verification.

Resend uses Svix for webhook delivery. Every request carries:
  - svix-id:        unique message identifier
  - svix-timestamp: unix timestamp (seconds)
  - svix-signature: space-separated list of "v1,<base64>" signatures

The signature is computed over:  {svix-id}.{svix-timestamp}.{raw_body}
using HMAC-SHA256 with the base64-decoded portion of the whsec_ secret.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TOLERANCE_SECONDS = 300  # 5 minutes


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


def verify_svix_signature(
    *,
    raw_body: bytes,
    svix_id: str | None,
    svix_timestamp: str | None,
    svix_signature: str | None,
    webhook_secret: str,
    tolerance: int = DEFAULT_TOLERANCE_SECONDS,
) -> bool:
    """Verify a Svix-compatible webhook signature (used by Resend).

    Args:
        raw_body: The exact raw request body as bytes.
        svix_id: Value of the svix-id header.
        svix_timestamp: Value of the svix-timestamp header.
        svix_signature: Value of the svix-signature header.
        webhook_secret: The whsec_... signing secret.
        tolerance: Max age in seconds (default 300 = 5 min).

    Returns:
        True if signature is valid.

    Raises:
        WebhookVerificationError with a descriptive reason on failure.
    """
    # ── check required headers ────────────────────────────────────────
    if not svix_id or not svix_timestamp or not svix_signature:
        raise WebhookVerificationError("Missing svix-* headers")

    # ── replay protection: timestamp tolerance ────────────────────────
    try:
        timestamp = int(svix_timestamp)
    except ValueError:
        raise WebhookVerificationError("Invalid svix-timestamp")

    now = int(time.time())
    if abs(now - timestamp) > tolerance:
        raise WebhookVerificationError(
            f"Timestamp {timestamp} is outside tolerance ({tolerance}s). "
            f"Server time: {now}. Diff: {abs(now - timestamp)}s"
        )

    # ── decode the signing secret ─────────────────────────────────────
    if not webhook_secret.startswith("whsec_"):
        raise WebhookVerificationError("Invalid webhook secret format (expected whsec_...)")

    secret_b64 = webhook_secret[6:]  # strip whsec_
    try:
        secret_bytes = base64.b64decode(secret_b64)
    except Exception:
        raise WebhookVerificationError("Failed to decode webhook secret")

    # ── compute expected signature ────────────────────────────────────
    signed_content = f"{svix_id}.{svix_timestamp}.{raw_body.decode('utf-8', errors='replace')}"
    expected_sig = base64.b64encode(
        hmac.new(secret_bytes, signed_content.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")

    # ── compare against provided signatures (may have multiple) ───────
    for token in svix_signature.split(" "):
        parts = token.split(",", 1)
        if len(parts) == 2:
            version, provided_sig = parts
            if version == "v1" and hmac.compare_digest(provided_sig, expected_sig):
                return True

    raise WebhookVerificationError("Signature mismatch")
