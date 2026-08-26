import pytest
from app.services.recovery.failure_diagnosis import (
    FailureCategory,
    FailureDiagnosisEngine,
    RecoveryStrategy,
)

engine = FailureDiagnosisEngine()


class TestUPI_TIMEOUT:
    def test_upi_timeout(self):
        r = engine.diagnose("UPI timeout")
        assert r.category == FailureCategory.UPI_TIMEOUT
        assert r.strategy == RecoveryStrategy.INSTANT_RETRY
        assert r.retry_after_seconds == 0
        assert r.max_retries == 3

    def test_timed_out(self):
        r = engine.diagnose("Payment timed out")
        assert r.category == FailureCategory.UPI_TIMEOUT

    def test_session_expired(self):
        r = engine.diagnose("Session expired during payment")
        assert r.category == FailureCategory.UPI_TIMEOUT

    def test_upi_timeout_case_insensitive(self):
        r = engine.diagnose("UPI TIMEOUT")
        assert r.category == FailureCategory.UPI_TIMEOUT


class TestBANK_DECLINED:
    def test_declined(self):
        r = engine.diagnose("Payment declined by issuing bank")
        assert r.category == FailureCategory.BANK_DECLINED
        assert r.strategy == RecoveryStrategy.DELAYED_RETRY
        assert r.retry_after_seconds == 3600
        assert r.max_retries == 2

    def test_insufficient_funds(self):
        r = engine.diagnose("Insufficient funds in account")
        assert r.category == FailureCategory.BANK_DECLINED

    def test_card_expired(self):
        r = engine.diagnose("Card expired")
        assert r.category == FailureCategory.BANK_DECLINED

    def test_blocked_by_issuer(self):
        r = engine.diagnose("Card blocked by issuer")
        assert r.category == FailureCategory.BANK_DECLINED

    def test_do_not_honor(self):
        r = engine.diagnose("Do not honor")
        assert r.category == FailureCategory.BANK_DECLINED


class TestNETWORK_ERROR:
    def test_network(self):
        r = engine.diagnose("Network failure during payment")
        assert r.category == FailureCategory.NETWORK_ERROR
        assert r.strategy == RecoveryStrategy.INSTANT_RETRY
        assert r.retry_after_seconds == 0
        assert r.max_retries == 3

    def test_connection_reset(self):
        r = engine.diagnose("Connection reset by peer")
        assert r.category == FailureCategory.NETWORK_ERROR

    def test_dns_resolution(self):
        r = engine.diagnose("DNS resolution failed")
        assert r.category == FailureCategory.NETWORK_ERROR


class TestGATEWAY_ERROR:
    def test_gateway(self):
        r = engine.diagnose("Bad gateway error")
        assert r.category == FailureCategory.GATEWAY_ERROR
        assert r.strategy == RecoveryStrategy.DELAYED_RETRY
        assert r.retry_after_seconds == 1800
        assert r.max_retries == 2

    def test_service_unavailable(self):
        r = engine.diagnose("Service unavailable")
        assert r.category == FailureCategory.GATEWAY_ERROR

    def test_502(self):
        r = engine.diagnose("HTTP 502 error")
        assert r.category == FailureCategory.GATEWAY_ERROR

    def test_503(self):
        r = engine.diagnose("503 service unavailable")
        assert r.category == FailureCategory.GATEWAY_ERROR


class TestFRAUD_CHECK:
    def test_fraud(self):
        r = engine.diagnose("Fraud check failed")
        assert r.category == FailureCategory.FRAUD_CHECK
        assert r.strategy == RecoveryStrategy.ESCALATE_TO_HUMAN
        assert r.max_retries == 0

    def test_suspicious(self):
        r = engine.diagnose("Suspicious activity detected")
        assert r.category == FailureCategory.FRAUD_CHECK

    def test_velocity_check(self):
        r = engine.diagnose("Velocity check exceeded")
        assert r.category == FailureCategory.FRAUD_CHECK

    def test_device_binding(self):
        r = engine.diagnose("Device binding mismatch detected")
        assert r.category == FailureCategory.FRAUD_CHECK

    def test_3ds_failed(self):
        r = engine.diagnose("3DS authentication failed")
        assert r.category == FailureCategory.FRAUD_CHECK


class TestUNKNOWN:
    def test_none(self):
        r = engine.diagnose(None)
        assert r.category == FailureCategory.UNKNOWN
        assert r.strategy == RecoveryStrategy.ALTERNATE_CHANNEL

    def test_empty(self):
        r = engine.diagnose("")
        assert r.category == FailureCategory.UNKNOWN

    def test_unrecognized(self):
        r = engine.diagnose("Something completely random happened")
        assert r.category == FailureCategory.UNKNOWN


class TestDiagnosisResult:
    def test_to_dict(self):
        r = engine.diagnose("UPI timeout")
        d = r.to_dict()
        assert d["category"] == "upi_timeout"
        assert d["strategy"] == "instant_retry"
        assert "raw_failure_reason" in d["context"]
        assert d["context"]["raw_failure_reason"] == "UPI timeout"
