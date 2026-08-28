from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from app.services.email.resend_service import (
    EmailSendErrorCategory,
    EmailSendResult,
    ResendEmailService,
    _classify_error,
    _MAX_RETRIES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class ResendAPIError(Exception):
    """Simulates a Resend SDK error with an optional status_code attribute."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _make_error(message: str, status_code: int | None = None) -> ResendAPIError:
    return ResendAPIError(message, status_code=status_code)


# ---------------------------------------------------------------------------
# _classify_error unit tests
# ---------------------------------------------------------------------------
class TestClassifyError:
    def test_rate_limit_429(self):
        assert _classify_error(_make_error("rate limit exceeded 429")) == EmailSendErrorCategory.RATE_LIMITED

    def test_rate_limit_keyword(self):
        assert _classify_error(_make_error("Too many requests, rate limited")) == EmailSendErrorCategory.RATE_LIMITED

    def test_auth_unauthorized(self):
        assert _classify_error(_make_error("unauthorized: invalid API key")) == EmailSendErrorCategory.AUTH_ERROR

    def test_auth_forbidden(self):
        assert _classify_error(_make_error("forbidden")) == EmailSendErrorCategory.AUTH_ERROR

    def test_auth_401(self):
        assert _classify_error(_make_error("401 authentication required")) == EmailSendErrorCategory.AUTH_ERROR

    def test_auth_403(self):
        assert _classify_error(_make_error("403 access denied")) == EmailSendErrorCategory.AUTH_ERROR

    def test_invalid_recipient(self):
        assert _classify_error(_make_error("invalid email address")) == EmailSendErrorCategory.INVALID_RECIPIENT

    def test_invalid_recipient_keyword(self):
        assert _classify_error(_make_error("recipient address is invalid")) == EmailSendErrorCategory.INVALID_RECIPIENT

    def test_server_error_defaults_to_provider(self):
        assert _classify_error(_make_error("internal server error")) == EmailSendErrorCategory.PROVIDER_ERROR

    def test_timeout_defaults_to_provider(self):
        assert _classify_error(_make_error("request timed out")) == EmailSendErrorCategory.PROVIDER_ERROR


# ---------------------------------------------------------------------------
# EmailSendResult unit tests
# ---------------------------------------------------------------------------
class TestEmailSendResult:
    def test_success_result(self):
        r = EmailSendResult(success=True, provider_message_id="re_abc123")
        assert r.success is True
        assert r.provider_message_id == "re_abc123"
        assert r.error_category is None
        assert r.is_retryable is False

    def test_retryable_rate_limited(self):
        r = EmailSendResult(success=False, error_category=EmailSendErrorCategory.RATE_LIMITED)
        assert r.is_retryable is True

    def test_retryable_provider_error(self):
        r = EmailSendResult(success=False, error_category=EmailSendErrorCategory.PROVIDER_ERROR)
        assert r.is_retryable is True

    def test_not_retryable_auth_error(self):
        r = EmailSendResult(success=False, error_category=EmailSendErrorCategory.AUTH_ERROR)
        assert r.is_retryable is False

    def test_not_retryable_invalid_recipient(self):
        r = EmailSendResult(success=False, error_category=EmailSendErrorCategory.INVALID_RECIPIENT)
        assert r.is_retryable is False


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — 429 rate limited
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailRateLimited:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_429_retries_then_fails(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("rate limit exceeded 429", status_code=429)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.RATE_LIMITED
        assert result.status_code == 429
        assert result.is_retryable is True
        assert mock_send.call_count == _MAX_RETRIES
        assert mock_sleep.call_count == _MAX_RETRIES - 1  # sleeps between retries, not after last

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_429_exponential_backoff_delays(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("rate limit 429", status_code=429)

        svc = ResendEmailService()
        await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert delays == [1.0, 2.0]


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — 500 server error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailServerError:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_500_retries_then_fails(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("internal server error", status_code=500)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.PROVIDER_ERROR
        assert result.status_code == 500
        assert result.is_retryable is True
        assert mock_send.call_count == _MAX_RETRIES

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_502_retries(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("bad gateway", status_code=502)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.PROVIDER_ERROR
        assert mock_send.call_count == _MAX_RETRIES

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_503_retries(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("service unavailable", status_code=503)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.PROVIDER_ERROR
        assert mock_send.call_count == _MAX_RETRIES


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — timeout
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailTimeout:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_timeout_retries_then_fails(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = asyncio.TimeoutError("request timed out")

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.PROVIDER_ERROR
        assert result.is_retryable is True
        assert mock_send.call_count == _MAX_RETRIES
        assert mock_sleep.call_count == _MAX_RETRIES - 1

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_timeout_error_message_preserved(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = asyncio.TimeoutError("connection timed out")

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert "connection timed out" in result.error_message


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — invalid token / auth error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailAuthToken:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_unauthorized_no_retry(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("unauthorized: invalid api key", status_code=401)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.AUTH_ERROR
        assert result.status_code == 401
        assert result.is_retryable is False
        assert mock_send.call_count == 1  # no retries
        mock_sleep.assert_not_called()

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_forbidden_no_retry(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("forbidden", status_code=403)

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.AUTH_ERROR
        assert mock_send.call_count == 1

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_api_key_error_no_retry(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("api_key is invalid or missing")

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.AUTH_ERROR
        assert mock_send.call_count == 1


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — invalid recipient (no retry)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailInvalidRecipient:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_invalid_email_no_retry(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = _make_error("invalid email address", status_code=422)

        svc = ResendEmailService()
        result = await svc.send_email(to="bad@", subject="S", body="<p>X</p>")

        assert result.success is False
        assert result.error_category == EmailSendErrorCategory.INVALID_RECIPIENT
        assert result.is_retryable is False
        assert mock_send.call_count == 1
        mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# ResendEmailService.send_email — success paths
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestSendEmailSuccess:
    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_success_on_first_attempt(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.return_value = {"id": "re_abc123def"}

        svc = ResendEmailService()
        result = await svc.send_email(to="user@test.com", subject="Hi", body="<p>Hello</p>")

        assert result.success is True
        assert result.provider_message_id == "re_abc123def"
        assert result.error_category is None
        mock_send.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_success_after_retry(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.side_effect = [
            _make_error("service unavailable", status_code=503),
            _make_error("service unavailable", status_code=503),
            {"id": "re_retry_ok"},
        ]

        svc = ResendEmailService()
        result = await svc.send_email(to="user@test.com", subject="Hi", body="<p>Hello</p>")

        assert result.success is True
        assert result.provider_message_id == "re_retry_ok"
        assert mock_send.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_uses_configured_sender(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "payments@recoverflow.in"
        mock_send.return_value = {"id": "re_x"}

        svc = ResendEmailService()
        await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        call_kwargs = mock_send.call_args[0][0]
        assert call_kwargs["from"] == "payments@recoverflow.in"

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_explicit_from_email_overrides_config(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "payments@recoverflow.in"
        mock_send.return_value = {"id": "re_x"}

        svc = ResendEmailService()
        await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>", from_email="custom@domain.com")

        call_kwargs = mock_send.call_args[0][0]
        assert call_kwargs["from"] == "custom@domain.com"

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_sends_to_recipient_list(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.return_value = {"id": "re_x"}

        svc = ResendEmailService()
        await svc.send_email(to="customer@example.com", subject="S", body="<p>X</p>")

        call_kwargs = mock_send.call_args[0][0]
        assert call_kwargs["to"] == ["customer@example.com"]

    @patch("app.services.email.resend_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.email.resend_service.resend.Emails.send")
    @patch("app.services.email.resend_service.settings")
    async def test_non_dict_response_returns_no_id(self, mock_settings, mock_send, mock_sleep):
        mock_settings.RECOVERY_EMAIL_FROM = "test@resend.dev"
        mock_send.return_value = "unexpected"

        svc = ResendEmailService()
        result = await svc.send_email(to="a@b.com", subject="S", body="<p>X</p>")

        assert result.success is True
        assert result.provider_message_id is None
