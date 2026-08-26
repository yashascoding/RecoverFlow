import pytest

from app.services.financial.financial_firewall import (
    BlockReason,
    FirewallConfig,
    FirewallResult,
    FinancialFirewall,
)


# ── Config defaults ─────────────────────────────────────────────────────────

class TestFirewallConfigDefaults:
    def test_default_max_auto_refund(self):
        assert FirewallConfig().max_auto_refund_paise == 500_000

    def test_default_max_auto_payment(self):
        assert FirewallConfig().max_auto_payment_paise == 500_000

    def test_default_allow_payment_modification(self):
        assert FirewallConfig().allow_payment_modification is False

    def test_default_require_refund_authorization(self):
        assert FirewallConfig().require_refund_authorization is True

    def test_config_is_frozen(self):
        cfg = FirewallConfig()
        with pytest.raises(AttributeError):
            cfg.max_auto_refund_paise = 100  # type: ignore[misc]


# ── Rule 1: Unauthorized refund ─────────────────────────────────────────────

class TestUnauthorizedRefund:
    def test_already_refunded_blocks(self):
        fw = FinancialFirewall()
        result = fw.check_refund(100_00, current_status="refunded")
        assert result.blocked is True
        assert result.allowed is False
        assert result.reason == BlockReason.UNAUTHORIZED_REFUND
        assert "already refunded" in result.message.lower()

    def test_wrong_status_blocks(self):
        fw = FinancialFirewall()
        for status in ["created", "authorized", "failed", "recovery_pending", "recovered"]:
            result = fw.check_refund(100_00, current_status=status)
            assert result.blocked is True
            assert result.reason == BlockReason.UNAUTHORIZED_REFUND
            assert status in result.message

    def test_captured_allows_small_refund(self):
        fw = FinancialFirewall()
        result = fw.check_refund(100_00, current_status="captured")
        assert result.allowed is True
        assert result.blocked is False

    def test_captured_blocks_unauthorized_large_refund(self):
        fw = FinancialFirewall()
        result = fw.check_refund(500_001, current_status="captured")
        assert result.blocked is True
        assert result.reason == BlockReason.UNAUTHORIZED_REFUND
        assert "exceeds" in result.message.lower()

    def test_captured_allows_authorized_large_refund(self):
        fw = FinancialFirewall()
        result = fw.check_refund(1_000_000, current_status="captured", authorized=True)
        assert result.allowed is True
        assert result.blocked is False

    def test_exactly_at_limit_allows(self):
        fw = FinancialFirewall()
        result = fw.check_refund(500_000, current_status="captured")
        assert result.allowed is True

    def test_one_over_limit_blocks(self):
        fw = FinancialFirewall()
        result = fw.check_refund(500_001, current_status="captured")
        assert result.blocked is True

    def test_custom_limit(self):
        fw = FinancialFirewall(FirewallConfig(max_auto_refund_paise=200_000))
        result = fw.check_refund(200_001, current_status="captured")
        assert result.blocked is True
        assert "2000" in result.message

        result = fw.check_refund(200_000, current_status="captured")
        assert result.allowed is True

    def test_zero_amount_refund(self):
        fw = FinancialFirewall()
        result = fw.check_refund(0, current_status="captured")
        assert result.allowed is True


# ── Rule 2: Payment modification ───────────────────────────────────────────

class TestPaymentModification:
    def test_captured_is_immutable(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="captured", target_status="failed"
        )
        assert result.blocked is True
        assert result.reason == BlockReason.PAYMENT_MODIFICATION
        assert "immutable" in result.message.lower()

    def test_refunded_is_immutable(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="refunded", target_status="captured"
        )
        assert result.blocked is True
        assert result.reason == BlockReason.PAYMENT_MODIFICATION

    def test_recovered_is_immutable(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="recovered", target_status="failed"
        )
        assert result.blocked is True
        assert result.reason == BlockReason.PAYMENT_MODIFICATION

    def test_created_can_be_modified(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="created", target_status="authorized"
        )
        assert result.allowed is True

    def test_failed_can_be_modified(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="failed", target_status="recovery_pending"
        )
        assert result.allowed is True

    def test_recovery_pending_can_be_modified(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="recovery_pending", target_status="recovered"
        )
        assert result.allowed is True

    def test_custom_config_allows_modification(self):
        fw = FinancialFirewall(FirewallConfig(allow_payment_modification=True))
        result = fw.check_payment_modification(
            current_status="captured", target_status="refunded"
        )
        assert result.allowed is True
        assert result.blocked is False

    def test_authorized_can_be_modified(self):
        fw = FinancialFirewall()
        result = fw.check_payment_modification(
            current_status="authorized", target_status="captured"
        )
        assert result.allowed is True


# ── Rule 3: High-value automation ───────────────────────────────────────────

class TestHighValueAutomation:
    def test_above_limit_blocks(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(500_001)
        assert result.blocked is True
        assert result.reason == BlockReason.HIGH_VALUE_AUTOMATION
        assert "exceeds" in result.message.lower()

    def test_at_limit_allows(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(500_000)
        assert result.allowed is True

    def test_below_limit_allows(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(499_999)
        assert result.allowed is True

    def test_custom_limit(self):
        fw = FinancialFirewall(FirewallConfig(max_auto_payment_paise=100_000))
        result = fw.check_auto_recovery(100_001)
        assert result.blocked is True
        assert "1000" in result.message

        result = fw.check_auto_recovery(100_000)
        assert result.allowed is True

    def test_zero_amount(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(0)
        assert result.allowed is True


# ── Rule 4: Duplicate recovery ──────────────────────────────────────────────

class TestDuplicateRecovery:
    def test_first_attempt_allowed(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(100_00, existing_attempts=0)
        assert result.allowed is True

    def test_existing_attempt_blocks(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(100_00, existing_attempts=1)
        assert result.blocked is True
        assert result.reason == BlockReason.DUPLICATE_RECOVERY
        assert "1 time" in result.message

    def test_multiple_existing_blocks(self):
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(100_00, existing_attempts=3)
        assert result.blocked is True
        assert "3 time" in result.message

    def test_high_value_checked_before_duplicate(self):
        """High-value fires first even with existing attempts."""
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(600_000, existing_attempts=1)
        assert result.reason == BlockReason.HIGH_VALUE_AUTOMATION

    def test_duplicate_not_checked_when_high_value(self):
        """If high-value blocks, duplicate rule is never reached."""
        fw = FinancialFirewall()
        result = fw.check_auto_recovery(600_000, existing_attempts=1)
        assert result.reason != BlockReason.DUPLICATE_RECOVERY


# ── FirewallResult ──────────────────────────────────────────────────────────

class TestFirewallResult:
    def test_allowed_result(self):
        r = FirewallResult(allowed=True)
        d = r.to_dict()
        assert d["allowed"] is True
        assert d["blocked"] is False
        assert d["reason"] is None

    def test_blocked_result(self):
        r = FirewallResult(
            allowed=False, blocked=True,
            reason=BlockReason.UNAUTHORIZED_REFUND,
            message="test",
        )
        d = r.to_dict()
        assert d["allowed"] is False
        assert d["blocked"] is True
        assert d["reason"] == "unauthorized_refund"
        assert d["message"] == "test"


# ── Full firewall with custom config ────────────────────────────────────────

class TestFullFirewall:
    def test_allows_legitimate_operations(self):
        fw = FinancialFirewall()
        assert fw.check_refund(100_00, current_status="captured").allowed
        assert fw.check_payment_modification(current_status="created", target_status="authorized").allowed
        assert fw.check_auto_recovery(100_00, existing_attempts=0).allowed

    def test_blocks_all_violations(self):
        fw = FinancialFirewall()
        assert fw.check_refund(100_00, current_status="refunded").blocked
        assert fw.check_payment_modification(current_status="captured", target_status="failed").blocked
        assert fw.check_auto_recovery(600_000).blocked
        assert fw.check_auto_recovery(100_00, existing_attempts=1).blocked
