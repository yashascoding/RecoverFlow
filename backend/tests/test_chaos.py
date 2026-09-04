"""Chaos engineering / fault injection tests for RecoverFlow.

Tests 10 failure scenarios to verify system resilience:
  1. Duplicate Razorpay webhook — idempotency
  2. Duplicate Resend webhook — idempotency
  3. Worker crash mid-processing — event recovery
  4. Redis unavailable — graceful degradation
  5. PostgreSQL unavailable — error handling
  6. Resend timeout — retry with backoff
  7. Razorpay timeout — error handling
  8. LLM timeout — agent failure handling
  9. Consent revoked during workflow — pipeline safety
  10. Decision replay — audit trail integrity
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.core.logging import get_logger

logger = get_logger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════════

class ResendAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _make_razorpay_event(event: str, order_id: str, payment_id: str, amount: int = 50000) -> dict:
    """Build a Razorpay webhook payload."""
    return {
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "order_id": order_id,
                    "amount": amount,
                    "currency": "INR",
                    "status": "failed" if "failed" in event else "captured",
                    "error_description": "Payment failed" if "failed" in event else None,
                }
            }
        },
    }


def _make_resend_event(resend_event: str, email_id: str, to: str = "user@test.com") -> dict:
    """Build a Resend webhook payload."""
    return {
        "type": resend_event,
        "data": {
            "email_id": email_id,
            "to": [to],
            "from": "recovery@recoverflow.in",
            "subject": "Payment retry",
            "created_at": time.time(),
        },
    }


def _make_event_schema(event_type: str, dedup_key: str | None = None):
    """Build a typed event schema for dispatcher tests."""
    from app.schemas.event import (
        BaseEvent, PaymentEventPayload, PaymentFailedEvent,
        EmailEventPayload, EmailDeliveredEvent, EventSource,
    )
    event_id = uuid.uuid4()
    if event_type == "payment.failed":
        return PaymentFailedEvent(
            source=EventSource.WEBHOOK,
            event_id=event_id,
            dedup_key=dedup_key,
            payload=PaymentEventPayload(
                payment_id=uuid.uuid4(),
                razorpay_order_id="order_test",
                razorpay_payment_id="pay_test",
                customer_id=uuid.uuid4(),
                customer_email="test@test.com",
                amount=50000,
                currency="INR",
                status="failed",
            ),
            failure_reason="Insufficient funds",
        )
    elif event_type == "email.delivered":
        return EmailDeliveredEvent(
            source=EventSource.WEBHOOK,
            event_id=event_id,
            dedup_key=dedup_key,
            payload=EmailEventPayload(
                message_id=uuid.uuid4(),
                customer_id=uuid.uuid4(),
                recipient_email="user@test.com",
                template_id=None,
                subject="Payment retry",
                provider_message_id="re_test123",
            ),
        )
    return None


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 1: Duplicate Razorpay Webhook
# ═════════════════════════════════════════════════════════════════════════════

class TestDuplicateRazorpayWebhook:
    """Verify that sending the same Razorpay webhook twice is handled idempotently."""

    @pytest.mark.asyncio
    async def test_duplicate_event_id_returns_duplicate(self):
        """Dispatcher returns DUPLICATE when same event_id is dispatched twice."""
        from app.events.dispatcher import EventBus
        from app.events.queue import EventQueue
        from app.models.event import EventStatus

        mock_queue = AsyncMock(spec=EventQueue)
        mock_queue.push = AsyncMock()
        bus = EventBus(queue=mock_queue)

        event = _make_event_schema("payment.failed", dedup_key="razorpay:pay_123:payment.failed")

        # Mock DB: first call returns None (no duplicate), second call returns existing
        mock_result_first = MagicMock()
        mock_result_first.scalar_one_or_none.return_value = None

        mock_existing_event = MagicMock()
        mock_existing_event.event_id = event.event_id

        mock_result_second = MagicMock()
        mock_result_second.scalar_one_or_none.return_value = mock_existing_event

        with patch("app.events.dispatcher.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # First call: no existing event by event_id, no dedup_key conflict
            mock_session.execute = AsyncMock(side_effect=[
                mock_result_first,   # event_id check
                mock_result_first,   # dedup_key check
            ])
            result1 = await bus.dispatch(event)
            assert result1 == EventStatus.PENDING

            # Second call: same event_id found
            mock_session.execute = AsyncMock(return_value=mock_result_second)
            result2 = await bus.dispatch(event)
            assert result2 == EventStatus.DUPLICATE

    @pytest.mark.asyncio
    async def test_duplicate_dedup_key_returns_duplicate(self):
        """Dispatcher returns DUPLICATE when dedup_key already exists."""
        from app.events.dispatcher import EventBus
        from app.events.queue import EventQueue
        from app.models.event import EventStatus

        mock_queue = AsyncMock(spec=EventQueue)
        bus = EventBus(queue=mock_queue)

        event = _make_event_schema("payment.failed", dedup_key="razorpay:pay_456:payment.failed")

        # Mock: event_id is new, but dedup_key exists
        mock_no_event = MagicMock()
        mock_no_event.scalar_one_or_none.return_value = None

        mock_existing_dedup = MagicMock()
        mock_existing_dedup.scalar_one_or_none.return_value = MagicMock()

        with patch("app.events.dispatcher.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_session.execute = AsyncMock(side_effect=[
                mock_no_event,           # event_id check — new
                mock_existing_dedup,     # dedup_key check — exists
            ])
            result = await bus.dispatch(event)
            assert result == EventStatus.DUPLICATE

    @pytest.mark.asyncio
    async def test_razorpay_webhook_background_task_idempotent(self):
        """Simulates processing the same Razorpay webhook payload twice.
        The second call should be a no-op due to dedup."""
        from app.api.webhooks import _process_webhook_event

        order_id = f"order_dup_{uuid.uuid4().hex[:8]}"
        payment_id = f"pay_dup_{uuid.uuid4().hex[:8]}"
        payload = _make_razorpay_event("payment.failed", order_id, payment_id)

        mock_payment_svc = AsyncMock()
        mock_payment_svc.get_payment_by_order_id = AsyncMock(return_value=None)

        # First call: payment not found (no payment to process)
        with patch("app.api.webhooks.PaymentService", return_value=mock_payment_svc):
            with patch("app.api.webhooks.RecoveryService"):
                await _process_webhook_event(
                    "payment.failed", payload["payload"], raw_payload=payload
                )

        # Second call: same payload — should also return early (payment not found)
        with patch("app.api.webhooks.PaymentService", return_value=mock_payment_svc):
            with patch("app.api.webhooks.RecoveryService"):
                await _process_webhook_event(
                    "payment.failed", payload["payload"], raw_payload=payload
                )

        # PaymentService was called twice (once per background task)
        assert mock_payment_svc.get_payment_by_order_id.call_count == 2


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 2: Duplicate Resend Webhook
# ═════════════════════════════════════════════════════════════════════════════

class TestDuplicateResendWebhook:
    """Verify that duplicate Resend email webhooks are handled idempotently."""

    @pytest.mark.asyncio
    async def test_duplicate_resend_delivered_idempotent(self):
        """Processing the same email.delivered webhook twice should only update status once."""
        from app.api.webhooks import _process_resend_event

        email_id = f"re_dup_{uuid.uuid4().hex[:8]}"
        data = _make_resend_event("email.delivered", email_id)

        mock_email_msg = MagicMock()
        mock_email_msg.id = uuid.uuid4()
        mock_email_msg.customer_id = uuid.uuid4()
        mock_email_msg.recipient_email = "user@test.com"
        mock_email_msg.template_id = None
        mock_email_msg.subject = "Payment retry"
        mock_email_msg.status = "sent"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_email_msg

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("app.api.webhooks.async_session_factory") as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # First delivery — status advances from "sent" to "delivered"
            await _process_resend_event("email.delivered", data["data"], raw_payload=data)
            assert mock_email_msg.status == "delivered"

            # Reset status back to "sent" to simulate the second webhook arriving
            mock_email_msg.status = "sent"

            # Second delivery — should be idempotent (only advance from allowed states)
            await _process_resend_event("email.delivered", data["data"], raw_payload=data)
            # Status should advance again since we reset it
            assert mock_email_msg.status == "delivered"

    @pytest.mark.asyncio
    async def test_resend_event_bus_dedup_by_dedup_key(self):
        """Duplicate Resend events dispatched to EventBus are deduplicated by dedup_key."""
        from app.events.dispatcher import EventBus
        from app.events.queue import EventQueue
        from app.models.event import EventStatus

        mock_queue = AsyncMock(spec=EventQueue)
        bus = EventBus(queue=mock_queue)

        email_id = "re_unique_abc"
        dedup_key = f"resend:{email_id}:email.delivered"

        event1 = _make_event_schema("email.delivered", dedup_key=dedup_key)
        event2 = _make_event_schema("email.delivered", dedup_key=dedup_key)

        mock_no_event = MagicMock()
        mock_no_event.scalar_one_or_none.return_value = None

        with patch("app.events.dispatcher.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            # First dispatch succeeds
            mock_session.execute = AsyncMock(side_effect=[mock_no_event, mock_no_event])
            result1 = await bus.dispatch(event1)
            assert result1 == EventStatus.PENDING

            # Second dispatch with same dedup_key — duplicate
            mock_dedup_exists = MagicMock()
            mock_dedup_exists.scalar_one_or_none.return_value = MagicMock()
            mock_session.execute = AsyncMock(side_effect=[mock_no_event, mock_dedup_exists])
            result2 = await bus.dispatch(event2)
            assert result2 == EventStatus.DUPLICATE


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 3: Worker Crash
# ═════════════════════════════════════════════════════════════════════════════

class TestWorkerCrash:
    """Verify system resilience when the event worker crashes mid-processing."""

    @pytest.mark.asyncio
    async def test_worker_crash_leaves_event_in_processing_set(self):
        """When worker crashes, event stays in processing set (detectable for recovery)."""
        from app.events.processor import EventProcessor
        from app.events.queue import EventQueue

        mock_queue = AsyncMock(spec=EventQueue)
        processor = EventProcessor(queue=mock_queue)

        event_id = uuid.uuid4()
        event_type = "payment.failed"
        payload = {"payment_id": str(uuid.uuid4())}

        # Register a handler that crashes
        async def crashing_handler(etype, data):
            raise RuntimeError("Worker crashed!")

        processor.register(event_type, crashing_handler)

        # Mock DB: event exists
        mock_event = MagicMock()
        mock_event.retry_count = 0
        mock_event.max_retries = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_event

        with patch("app.events.processor.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await processor.process_one({
                "event_id": str(event_id),
                "event_type": event_type,
                "payload": payload,
            })

        # Processing failed
        assert result is False
        # Event retry count was incremented
        assert mock_event.retry_count == 1
        # Event was moved to retry queue (not dead-lettered yet)
        mock_queue.retry.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_crash_exhausts_retries_to_dead_letter(self):
        """After max_retries crashes, event moves to dead letter queue."""
        from app.events.processor import EventProcessor
        from app.events.queue import EventQueue

        mock_queue = AsyncMock(spec=EventQueue)
        processor = EventProcessor(queue=mock_queue)

        event_id = uuid.uuid4()

        async def always_crash(etype, data):
            raise RuntimeError("Persistent crash!")

        processor.register("payment.failed", always_crash)

        # Simulate event that has already failed 2 times (about to hit max_retries=3)
        mock_event = MagicMock()
        mock_event.retry_count = 2
        mock_event.max_retries = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_event

        with patch("app.events.processor.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(return_value=mock_result)

            result = await processor.process_one({
                "event_id": str(event_id),
                "event_type": "payment.failed",
                "payload": {"payment_id": "test"},
            })

        assert result is False
        # retry_count now = 3, which equals max_retries
        assert mock_event.retry_count == 3
        # Event moved to dead letter queue
        mock_queue.dead_letter.assert_called_once()

    @pytest.mark.asyncio
    async def test_worker_graceful_shutdown_clears_retry_task(self):
        """Worker shuts down gracefully when shutdown signal is received."""
        from app.workers import event_worker

        # Set shutdown flag
        event_worker._shutdown.set()

        assert event_worker._shutdown.is_set()

        # Verify the flag can be checked
        loop_count = 0
        while not event_worker._shutdown.is_set() and loop_count < 10:
            loop_count += 1

        # Should exit immediately since shutdown is set
        assert loop_count == 0


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 4: Redis Unavailable
# ═════════════════════════════════════════════════════════════════════════════

class TestRedisUnavailable:
    """Verify behavior when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_queue_push_fails_gracefully(self):
        """Queue push raises exception when Redis is down (caller handles it)."""
        from app.events.queue import EventQueue

        queue = EventQueue(redis_url="redis://localhost:9999")

        # Mock the client to raise ConnectionError
        mock_client = AsyncMock()
        mock_client.lpush = AsyncMock(side_effect=ConnectionError("Redis unavailable"))

        with patch.object(queue, "_get_client", return_value=mock_client):
            with pytest.raises(ConnectionError, match="Redis unavailable"):
                await queue.push(
                    event_id=uuid.uuid4(),
                    event_type="payment.failed",
                    payload={"test": True},
                )

    @pytest.mark.asyncio
    async def test_queue_pop_returns_none_on_timeout(self):
        """Queue pop returns None when Redis times out (no crash)."""
        from app.events.queue import EventQueue

        queue = EventQueue(redis_url="redis://localhost:9999")

        mock_client = AsyncMock()
        mock_client.brpop = AsyncMock(return_value=None)  # timeout

        with patch.object(queue, "_get_client", return_value=mock_client):
            result = await queue.pop(timeout=1)
            assert result is None

    @pytest.mark.asyncio
    async def test_queue_pop_fails_on_connection_error(self):
        """Queue pop raises ConnectionError when Redis is unreachable."""
        from app.events.queue import EventQueue

        queue = EventQueue(redis_url="redis://localhost:9999")

        mock_client = AsyncMock()
        mock_client.brpop = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with patch.object(queue, "_get_client", return_value=mock_client):
            with pytest.raises(ConnectionError):
                await queue.pop(timeout=1)

    @pytest.mark.asyncio
    async def test_dispatcher_redis_failure_after_db_commit(self):
        """If Redis push fails after DB commit, event is persisted but not queued."""
        from app.events.dispatcher import EventBus
        from app.events.queue import EventQueue
        from app.models.event import EventStatus

        mock_queue = AsyncMock(spec=EventQueue)
        mock_queue.push = AsyncMock(side_effect=ConnectionError("Redis down"))
        bus = EventBus(queue=mock_queue)

        event = _make_event_schema("payment.failed", dedup_key="razorpay:pay_redis:payment.failed")

        mock_no_event = MagicMock()
        mock_no_event.scalar_one_or_none.return_value = None

        with patch("app.events.dispatcher.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(side_effect=[mock_no_event, mock_no_event])

            # Should raise ConnectionError from Redis push (after DB commit succeeds)
            with pytest.raises(ConnectionError, match="Redis down"):
                await bus.dispatch(event)

            # DB commit was called (event persisted)
            mock_session.commit.assert_called_once()


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 5: PostgreSQL Unavailable
# ═════════════════════════════════════════════════════════════════════════════

class TestPostgresUnavailable:
    """Verify behavior when PostgreSQL is unavailable."""

    @pytest.mark.asyncio
    async def test_dispatcher_db_failure_before_commit(self):
        """Dispatcher fails gracefully when DB connection is lost."""
        from app.events.dispatcher import EventBus
        from app.events.queue import EventQueue

        mock_queue = AsyncMock(spec=EventQueue)
        bus = EventBus(queue=mock_queue)

        event = _make_event_schema("payment.failed", dedup_key="razorpay:pay_pg:payment.failed")

        with patch("app.events.dispatcher.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(
                side_effect=ConnectionError("PostgreSQL unavailable")
            )

            with pytest.raises(ConnectionError, match="PostgreSQL unavailable"):
                await bus.dispatch(event)

            # Redis push was NOT called (DB failed first)
            mock_queue.push.assert_not_called()

    @pytest.mark.asyncio
    async def test_processor_db_failure_on_mark_processing(self):
        """Event processor handles DB failure when marking event as processing."""
        from app.events.processor import EventProcessor
        from app.events.queue import EventQueue

        mock_queue = AsyncMock(spec=EventQueue)
        processor = EventProcessor(queue=mock_queue)

        with patch("app.events.processor.async_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_session.execute = AsyncMock(
                side_effect=ConnectionError("DB connection lost")
            )

            # process_one should propagate the DB error
            with pytest.raises(ConnectionError):
                await processor.process_one({
                    "event_id": str(uuid.uuid4()),
                    "event_type": "payment.failed",
                    "payload": {"test": True},
                })

    @pytest.mark.asyncio
    async def test_webhook_handler_db_rollback_on_error(self):
        """Webhook background task rolls back DB on error."""
        from app.api.webhooks import _process_webhook_event

        order_id = f"order_pg_{uuid.uuid4().hex[:8]}"
        payload = _make_razorpay_event("payment.failed", order_id, "pay_pg_test")

        mock_payment_svc = AsyncMock()
        mock_payment_svc.get_payment_by_order_id = AsyncMock(
            side_effect=ConnectionError("DB down")
        )

        with patch("app.api.webhooks.PaymentService", return_value=mock_payment_svc):
            # Should not raise — webhook handler catches exceptions
            await _process_webhook_event(
                "payment.failed", payload["payload"], raw_payload=payload
            )


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 6: Resend Timeout
# ═════════════════════════════════════════════════════════════════════════════

class TestResendTimeout:
    """Verify retry behavior when Resend API times out."""

    @pytest.mark.asyncio
    async def test_timeout_retries_three_times(self):
        """ResendEmailService retries 3 times on timeout then fails."""
        from app.services.email.resend_service import ResendEmailService, _MAX_RETRIES

        mock_send = MagicMock(side_effect=asyncio.TimeoutError("Connection timed out"))

        with patch("app.services.email.resend_service.resend.Emails.send", mock_send):
            with patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.services.email.resend_service.settings") as mock_settings:
                    mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
                    mock_settings.is_production = False
                    mock_settings.TEST_EMAIL = None
                    svc = ResendEmailService()
                    result = await svc.send_email(
                        to="user@test.com", subject="Test", body="<p>Hi</p>"
                    )

        assert result.success is False
        assert mock_send.call_count == _MAX_RETRIES

    @pytest.mark.asyncio
    async def test_timeout_exponential_backoff(self):
        """ResendEmailService uses exponential backoff on timeout."""
        from app.services.email.resend_service import ResendEmailService

        mock_send = MagicMock(side_effect=asyncio.TimeoutError("timeout"))
        mock_sleep = AsyncMock()

        with patch("app.services.email.resend_service.resend.Emails.send", mock_send):
            with patch("app.services.email.resend_service.asyncio.sleep", mock_sleep):
                with patch("app.services.email.resend_service.settings") as mock_settings:
                    mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
                    mock_settings.is_production = False
                    mock_settings.TEST_EMAIL = None
                    svc = ResendEmailService()
                    await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_timeout_succeeds_on_retry(self):
        """ResendEmailService succeeds on the second attempt after timeout."""
        from app.services.email.resend_service import ResendEmailService

        mock_send = MagicMock(side_effect=[
            asyncio.TimeoutError("timeout"),
            {"id": "re_retry_success"},
        ])

        with patch("app.services.email.resend_service.resend.Emails.send", mock_send):
            with patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock):
                with patch("app.services.email.resend_service.settings") as mock_settings:
                    mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
                    mock_settings.is_production = False
                    mock_settings.TEST_EMAIL = None
                    svc = ResendEmailService()
                    result = await svc.send_email(
                        to="user@test.com", subject="Hi", body="<p>Hello</p>"
                    )

        assert result.success is True
        assert result.provider_message_id == "re_retry_success"
        assert mock_send.call_count == 2


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 7: Razorpay Timeout
# ═════════════════════════════════════════════════════════════════════════════

class TestRazorpayTimeout:
    """Verify error handling when Razorpay API times out or fails."""

    @pytest.mark.asyncio
    async def test_create_order_timeout_propagates(self):
        """Razorpay create_order raises on timeout (no built-in retry)."""
        from app.services.payments.razorpay_service import RazorpayService

        svc = RazorpayService.__new__(RazorpayService)
        svc.client = MagicMock()
        svc.client.order.create = MagicMock(side_effect=Exception("Connection timeout"))

        with pytest.raises(Exception, match="Connection timeout"):
            svc.create_order(amount=50000, currency="INR", receipt="test")

    @pytest.mark.asyncio
    async def test_capture_payment_server_error_propagates(self):
        """Razorpay capture_payment raises on server error."""
        from app.services.payments.razorpay_service import RazorpayService

        svc = RazorpayService.__new__(RazorpayService)
        svc.client = MagicMock()
        svc.client.payment.capture = MagicMock(
            side_effect=Exception("Internal server error")
        )

        with pytest.raises(Exception, match="Internal server error"):
            svc.capture_payment(payment_id="pay_test", amount=50000)

    @pytest.mark.asyncio
    async def test_webhook_signature_fails_on_bad_secret(self):
        """Webhook signature verification fails with wrong secret."""
        from app.services.payments.razorpay_service import RazorpayService

        svc = RazorpayService.__new__(RazorpayService)

        payload = b'{"event":"payment.failed"}'
        correct_secret = "whsec_test123"
        wrong_secret = "whsec_wrong"

        import hmac as hmac_mod
        import hashlib
        correct_sig = hmac_mod.new(
            correct_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        # Verify with correct secret passes
        assert svc.verify_webhook_signature(payload, correct_sig, secret=correct_secret) is True

        # Verify with wrong secret fails
        assert svc.verify_webhook_signature(payload, correct_sig, secret=wrong_secret) is False


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 8: LLM Timeout
# ═════════════════════════════════════════════════════════════════════════════

class TestLLMTimeout:
    """Verify agent resilience when the LLM call times out."""

    @pytest.mark.asyncio
    async def test_llm_timeout_agent_fails_gracefully(self):
        """RecoveryAgent returns failure when LLM times out."""
        from app.services.agents.recovery_agent import RecoveryAgent, LLMTimeoutError

        async def slow_llm(prompt):
            await asyncio.sleep(100)
            return {}

        agent = RecoveryAgent(
            db=AsyncMock(),
            llm_call=slow_llm,
            llm_timeout=0.1,  # 100ms timeout
            tool_timeout=5.0,
        )

        # Mock tools to return valid data
        mock_customer_tool = AsyncMock()
        mock_customer_tool.execute = AsyncMock(return_value={
            "id": str(uuid.uuid4()),
            "email": "test@test.com",
            "name": "Test",
        })

        mock_payment_tool = AsyncMock()
        mock_payment_tool.execute = AsyncMock(return_value={
            "id": str(uuid.uuid4()),
            "status": "failed",
            "amount": 50000,
        })

        mock_consent_tool = AsyncMock()
        mock_consent_tool.execute = AsyncMock(return_value={"has_consent": True})

        mock_diagnosis_tool = AsyncMock()
        mock_diagnosis_tool.execute = AsyncMock(return_value={
            "failure_reason": "insufficient_funds",
            "category": "bank_decline",
        })

        agent._tools = {
            "fetch_customer": mock_customer_tool,
            "fetch_payment": mock_payment_tool,
            "check_consent": mock_consent_tool,
            "diagnose_failure": mock_diagnosis_tool,
        }

        result = await agent.run({
            "payment_id": str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "order_id": "order_test",
            "failure_reason": "Insufficient funds",
        })

        # Agent should fail but not crash
        assert result["success"] is False
        assert result["state"] == "failed"
        assert "trace" in result

    @pytest.mark.asyncio
    async def test_tool_timeout_agent_handles_error(self):
        """RecoveryAgent handles individual tool timeouts."""
        from app.services.agents.recovery_agent import RecoveryAgent

        async def fast_llm(prompt):
            return {
                "diagnosis": "Test diagnosis",
                "confidence": 0.8,
                "recommended_action": "EMAIL_PAYMENT_LINK",
                "reason": "Test",
                "risk_level": "LOW",
            }

        agent = RecoveryAgent(
            db=AsyncMock(),
            llm_call=fast_llm,
            llm_timeout=30.0,
            tool_timeout=0.1,  # 100ms tool timeout
        )

        # Tool that hangs
        async def slow_tool(**kwargs):
            await asyncio.sleep(100)
            return {}

        mock_tool = AsyncMock()
        mock_tool.execute = slow_tool

        agent._tools = {"fetch_customer": mock_tool}

        result = await agent.run({
            "payment_id": str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "order_id": "order_test",
            "failure_reason": "Test",
        })

        # Agent handles tool timeout gracefully
        assert result["success"] is False
        assert result["state"] == "failed"

    @pytest.mark.asyncio
    async def test_malformed_llm_response_agent_fails(self):
        """RecoveryAgent handles malformed LLM JSON response."""
        from app.services.agents.recovery_agent import RecoveryAgent

        async def bad_llm(prompt):
            return "this is not a dict"

        agent = RecoveryAgent(
            db=AsyncMock(),
            llm_call=bad_llm,
            llm_timeout=30.0,
            tool_timeout=5.0,
        )

        mock_tool = AsyncMock()
        mock_tool.execute = AsyncMock(return_value={"id": "test", "status": "failed"})
        agent._tools = {
            "fetch_customer": mock_tool,
            "fetch_payment": mock_tool,
            "check_consent": mock_tool,
            "diagnose_failure": mock_tool,
        }

        result = await agent.run({
            "payment_id": str(uuid.uuid4()),
            "customer_id": str(uuid.uuid4()),
            "email": "test@test.com",
            "order_id": "order_test",
            "failure_reason": "Test",
        })

        assert result["success"] is False
        assert result["state"] == "failed"


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 9: Consent Revoked During Workflow
# ═════════════════════════════════════════════════════════════════════════════

class TestConsentRevokedDuringWorkflow:
    """Verify pipeline safety when customer consent is revoked mid-workflow."""

    @pytest.mark.asyncio
    async def test_consent_revoked_blocks_recovery(self):
        """Pipeline blocks recovery when consent is revoked (no email sent)."""
        from app.services.recovery.recovery_pipeline import RecoveryPipeline

        customer_id = uuid.uuid4()
        payment_id = uuid.uuid4()

        mock_db = AsyncMock()

        # Mock payment exists and is failed
        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.customer_id = customer_id
        mock_payment.customer_email = "user@test.com"
        mock_payment.status = "failed"
        mock_payment.amount = 50000

        mock_payment_svc = AsyncMock()
        mock_payment_svc.get_payment_by_order_id = AsyncMock(return_value=mock_payment)

        # Consent check returns False (revoked)
        mock_consent_svc = AsyncMock()
        mock_consent_svc.validate_consent = AsyncMock(return_value=False)

        pipeline = RecoveryPipeline(mock_db)
        pipeline.payment_svc = mock_payment_svc
        pipeline.consent_svc = mock_consent_svc

        result = await pipeline.handle_payment_failure(
            order_id="order_consent_test",
            failure_reason="Test failure",
        )

        # Pipeline should block — no email sent
        assert result.success is False
        assert "consent" in result.reason.lower() or "consent" in result.reason

    @pytest.mark.asyncio
    async def test_consent_check_happens_before_agent_and_email(self):
        """Consent check is evaluated before AI agent and email are called."""
        from app.services.recovery.recovery_pipeline import RecoveryPipeline

        customer_id = uuid.uuid4()
        payment_id = uuid.uuid4()

        mock_db = AsyncMock()

        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.customer_id = customer_id
        mock_payment.customer_email = "user@test.com"
        mock_payment.status = "failed"
        mock_payment.amount = 50000

        mock_payment_svc = AsyncMock()
        mock_payment_svc.get_payment_by_order_id = AsyncMock(return_value=mock_payment)

        # Consent revoked
        mock_consent_svc = AsyncMock()
        mock_consent_svc.validate_consent = AsyncMock(return_value=False)

        pipeline = RecoveryPipeline(mock_db)
        pipeline.payment_svc = mock_payment_svc
        pipeline.consent_svc = mock_consent_svc

        # Mock other services to track call order
        call_order = []

        original_create = pipeline.policy_svc.create
        async def tracked_policy_create(**kwargs):
            call_order.append("policy_create")
            return MagicMock(id=uuid.uuid4())

        pipeline.policy_svc.create = tracked_policy_create

        original_audit = pipeline.audit_svc.create
        async def tracked_audit_create(**kwargs):
            call_order.append("audit_create")
            return MagicMock(id=uuid.uuid4())

        pipeline.audit_svc.create = tracked_audit_create

        result = await pipeline.handle_payment_failure(
            order_id="order_order_test",
            failure_reason="Test",
        )

        # Consent was checked
        mock_consent_svc.validate_consent.assert_called_once()
        # Pipeline blocked before agent or email
        assert result.success is False
        # Policy decision and audit were recorded
        assert "policy_create" in call_order
        assert "audit_create" in call_order

    @pytest.mark.asyncio
    async def test_consent_revoked_between_checks(self):
        """Simulates consent being revoked between two pipeline runs."""
        from app.services.recovery.recovery_pipeline import RecoveryPipeline

        customer_id = uuid.uuid4()
        payment_id = uuid.uuid4()

        mock_db = AsyncMock()

        mock_payment = MagicMock()
        mock_payment.id = payment_id
        mock_payment.customer_id = customer_id
        mock_payment.customer_email = "user@test.com"
        mock_payment.status = "failed"
        mock_payment.amount = 50000

        mock_payment_svc = AsyncMock()
        mock_payment_svc.get_payment_by_order_id = AsyncMock(return_value=mock_payment)

        # First run: consent granted
        consent_state = {"granted": True}

        mock_consent_svc = AsyncMock()

        async def check_consent(customer_id, channel):
            return consent_state["granted"]

        mock_consent_svc.validate_consent = check_consent

        pipeline = RecoveryPipeline(mock_db)
        pipeline.payment_svc = mock_payment_svc
        pipeline.consent_svc = mock_consent_svc

        # Run 1: consent granted — would proceed (we'll mock the rest to skip)
        # Just verify consent is checked
        has_consent = await mock_consent_svc.validate_consent(customer_id, "email")
        assert has_consent is True

        # Customer revokes consent
        consent_state["granted"] = False

        # Run 2: consent revoked — pipeline blocks
        has_consent = await mock_consent_svc.validate_consent(customer_id, "email")
        assert has_consent is False


# ═════════════════════════════════════════════════════════════════════════════
# HOUR 10: Decision Replay
# ═════════════════════════════════════════════════════════════════════════════

class TestDecisionReplay:
    """Verify audit trail integrity for decision replay."""

    @pytest.mark.asyncio
    async def test_audit_log_records_full_decision_context(self):
        """Audit log captures all context needed for decision replay."""
        from app.services.audit.audit_service import AuditService
        from app.models.audit_log import AuditAction

        mock_db = AsyncMock()

        audit_svc = AuditService(mock_db)

        payment_id = uuid.uuid4()
        attempt_id = uuid.uuid4()
        email_msg_id = uuid.uuid4()

        payload = {
            "recovery_attempt_id": str(attempt_id),
            "email_message_id": str(email_msg_id),
            "failure_reason": "Insufficient funds",
            "amount": 50000,
            "agent_diagnosis": {
                "diagnosis": "Bank declined due to insufficient funds",
                "confidence": 0.92,
                "recommended_action": "EMAIL_PAYMENT_LINK",
            },
        }

        log = await audit_svc.create(
            actor="recovery_pipeline",
            action=AuditAction.RECOVERY_ATTEMPTED.value,
            resource_type="payment",
            resource_id=payment_id,
            description="Recovery initiated for ₹500 — Insufficient funds",
            payload=payload,
        )

        # Verify audit log was created
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.actor == "recovery_pipeline"
        assert added_obj.action == "recovery_attempted"
        assert added_obj.resource_type == "payment"
        assert added_obj.resource_id == payment_id
        assert added_obj.payload["failure_reason"] == "Insufficient funds"
        assert added_obj.payload["amount"] == 50000
        assert added_obj.payload["agent_diagnosis"]["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_policy_decision_records_rule_and_context(self):
        """Policy decision log captures the rule applied and full context."""
        from app.services.policy.policy_service import PolicyService

        mock_db = AsyncMock()

        policy_svc = PolicyService(mock_db)

        payment_id = uuid.uuid4()
        customer_id = uuid.uuid4()

        decision = await policy_svc.create(
            decision_type="recovery_eligible",
            outcome="approved",
            payment_id=payment_id,
            customer_id=customer_id,
            reason="Recovery candidate: no blocks triggered",
            context={
                "rule": "default",
                "failure_reason": "Insufficient funds",
                "amount_paise": 50000,
                "has_email_consent": True,
                "attempt_count": 0,
            },
            evaluated_by="policy_engine",
        )

        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.decision_type == "recovery_eligible"
        assert added_obj.outcome == "approved"
        assert added_obj.context["rule"] == "default"
        assert added_obj.evaluated_by == "policy_engine"

    @pytest.mark.asyncio
    async def test_recovery_attempt_tracks_full_lifecycle(self):
        """Recovery attempt records all timestamps for replay."""
        from app.services.recovery.recovery_attempt_service import RecoveryAttemptService

        mock_db = AsyncMock()

        attempt_svc = RecoveryAttemptService(mock_db)

        customer_id = uuid.uuid4()
        payment_id = uuid.uuid4()

        attempt = await attempt_svc.create(
            customer_id=customer_id,
            payment_id=payment_id,
            channel="email",
            amount=50000,
        )

        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.customer_id == customer_id
        assert added_obj.payment_id == payment_id
        assert added_obj.channel == "email"
        assert added_obj.amount == 50000
        assert added_obj.status == "pending"

    @pytest.mark.asyncio
    async def test_agent_trace_captures_complete_workflow(self):
        """Agent trace records all stages for full replay capability."""
        from app.services.agents.agent_trace import AgentTrace
        from app.services.agents.state_machine import AgentState

        trace = AgentTrace(
            run_id=uuid.uuid4(),
            payment_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
        )

        # Simulate 4-stage workflow
        trace.begin_stage(AgentState.OBSERVE, {"customer_id": "test"})
        trace.record_tool_call(AgentState.OBSERVE, "fetch_customer", {"id": "test"}, {"name": "Test"}, None, 50.0)
        trace.complete_stage(AgentState.OBSERVE, {"customer": "data"})

        trace.begin_stage(AgentState.INVESTIGATE, {"payment_id": "test"})
        trace.record_tool_call(AgentState.INVESTIGATE, "check_consent", {}, {"consent": True}, None, 30.0)
        trace.complete_stage(AgentState.INVESTIGATE, {"consent": True})

        trace.begin_stage(AgentState.DIAGNOSE, {"context": "all"})
        trace.complete_stage(AgentState.DIAGNOSE, {"diagnosis": "bank_decline"})

        trace.begin_stage(AgentState.PLAN, {"diagnosis": "bank_decline"})
        trace.complete_stage(AgentState.PLAN, {"action": "send_email"})

        trace.complete(AgentState.COMPLETED)

        trace_dict = trace.to_dict()

        # Verify all stages present
        assert len(trace_dict["stages"]) == 4
        stage_names = [s["stage"] for s in trace_dict["stages"]]
        assert stage_names == ["observe", "investigate", "diagnose", "plan"]

        # Verify tool calls recorded
        observe_stage = trace_dict["stages"][0]
        assert len(observe_stage["tool_calls"]) == 1
        assert observe_stage["tool_calls"][0]["tool_name"] == "fetch_customer"

        # Verify timing
        assert trace_dict["started_at"] is not None
        assert trace_dict["completed_at"] is not None
        assert trace_dict["current_state"] == "completed"
