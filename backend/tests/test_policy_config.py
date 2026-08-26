import pytest

from app.services.policy.policy_engine import (
    PolicyConfig,
    PolicyContext,
    PolicyEngine,
    PolicyResult,
    PolicyVerdict,
)


# ── PolicyConfig defaults ───────────────────────────────────────────────────

class TestPolicyConfigDefaults:
    def test_default_max_auto_payment(self):
        cfg = PolicyConfig()
        assert cfg.max_auto_payment == 500_000  # ₹5,000

    def test_default_max_emails_per_day(self):
        cfg = PolicyConfig()
        assert cfg.max_emails_per_day == 1

    def test_default_required_opt_in(self):
        cfg = PolicyConfig()
        assert cfg.required_opt_in is True

    def test_default_human_review_above(self):
        cfg = PolicyConfig()
        assert cfg.human_review_above == 500_000  # ₹5,000

    def test_config_is_frozen(self):
        cfg = PolicyConfig()
        with pytest.raises(AttributeError):
            cfg.max_auto_payment = 1000  # type: ignore[misc]


class TestPolicyConfigCustomValues:
    def test_custom_config(self):
        cfg = PolicyConfig(
            max_auto_payment=200_000,
            max_emails_per_day=3,
            required_opt_in=False,
            human_review_above=200_000,
        )
        assert cfg.max_auto_payment == 200_000
        assert cfg.max_emails_per_day == 3
        assert cfg.required_opt_in is False
        assert cfg.human_review_above == 200_000


# ── required_opt_in ─────────────────────────────────────────────────────────

class TestRequiredOptIn:
    def test_blocks_when_opt_in_required_and_no_consent(self):
        cfg = PolicyConfig(required_opt_in=True)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "no_consent"

    def test_passes_when_opt_in_required_and_consent_given(self):
        cfg = PolicyConfig(required_opt_in=True)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.rule != "no_consent"

    def test_no_consent_passes_when_opt_in_not_required(self):
        cfg = PolicyConfig(required_opt_in=False)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.rule != "no_consent"
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE


# ── max_auto_payment / human_review_above ───────────────────────────────────

class TestMaxAutoPayment:
    def test_above_threshold_triggers_human_review(self):
        cfg = PolicyConfig(max_auto_payment=300_000, human_review_above=300_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=300_001,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW
        assert result.rule == "high_value"

    def test_at_threshold_is_candidate(self):
        cfg = PolicyConfig(max_auto_payment=300_000, human_review_above=300_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=300_000,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE

    def test_below_threshold_is_candidate(self):
        cfg = PolicyConfig(max_auto_payment=300_000, human_review_above=300_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=299_999,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE

    def test_custom_threshold_of_1000(self):
        cfg = PolicyConfig(max_auto_payment=100_000, human_review_above=100_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_001,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW

    def test_human_review_above_uses_config(self):
        cfg = PolicyConfig(human_review_above=200_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=200_001,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW
        assert "2,000" in result.reason


# ── max_emails_per_day ──────────────────────────────────────────────────────

class TestMaxEmailsPerDay:
    def test_blocks_when_limit_reached(self):
        cfg = PolicyConfig(max_emails_per_day=1)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=1,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "daily_limit"
        assert "1/1" in result.reason

    def test_passes_when_under_limit(self):
        cfg = PolicyConfig(max_emails_per_day=1)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=0,
        )
        result = engine.evaluate(ctx)
        assert result.rule != "daily_limit"

    def test_custom_limit_of_3(self):
        cfg = PolicyConfig(max_emails_per_day=3)
        engine = PolicyEngine(cfg)

        # 2 sent, limit 3 → should pass
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=2,
        )
        result = engine.evaluate(ctx)
        assert result.rule != "daily_limit"

        # 3 sent, limit 3 → should block
        ctx.emails_sent_today = 3
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "daily_limit"
        assert "3/3" in result.reason

    def test_limit_of_zero_blocks_all(self):
        cfg = PolicyConfig(max_emails_per_day=0)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=0,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "daily_limit"

    def test_daily_limit_priority_after_consent(self):
        """no_consent fires before daily_limit."""
        cfg = PolicyConfig(required_opt_in=True, max_emails_per_day=1)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=1,
        )
        result = engine.evaluate(ctx)
        assert result.rule == "no_consent"

    def test_daily_limit_priority_before_high_value(self):
        """daily_limit fires before high_value."""
        cfg = PolicyConfig(max_emails_per_day=1, human_review_above=100_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=200_000,
            is_already_recovered=False,
            emails_sent_today=1,
        )
        result = engine.evaluate(ctx)
        assert result.rule == "daily_limit"


# ── Rule priority ordering ──────────────────────────────────────────────────

class TestRuleOrderingWithConfig:
    def test_full_priority_chain(self):
        """Verify: no_consent > daily_limit > high_value > already_recovered > default."""
        cfg = PolicyConfig(required_opt_in=True, max_emails_per_day=1, human_review_above=500_000)
        engine = PolicyEngine(cfg)

        # 1. no_consent wins over everything
        ctx = PolicyContext(
            has_email_consent=False, amount_paise=1_000_000,
            is_already_recovered=True, emails_sent_today=5,
        )
        assert engine.evaluate(ctx).rule == "no_consent"

        # 2. daily_limit wins over high_value + already_recovered
        ctx = PolicyContext(
            has_email_consent=True, amount_paise=1_000_000,
            is_already_recovered=True, emails_sent_today=1,
        )
        assert engine.evaluate(ctx).rule == "daily_limit"

        # 3. high_value wins over already_recovered
        ctx = PolicyContext(
            has_email_consent=True, amount_paise=600_000,
            is_already_recovered=True, emails_sent_today=0,
        )
        assert engine.evaluate(ctx).rule == "high_value"

        # 4. already_recovered
        ctx = PolicyContext(
            has_email_consent=True, amount_paise=100_00,
            is_already_recovered=True, emails_sent_today=0,
        )
        assert engine.evaluate(ctx).rule == "already_recovered"

        # 5. default
        ctx = PolicyContext(
            has_email_consent=True, amount_paise=100_00,
            is_already_recovered=False, emails_sent_today=0,
        )
        assert engine.evaluate(ctx).rule == "default"


# ── Result context includes config info ─────────────────────────────────────

class TestResultContext:
    def test_daily_limit_context_includes_limits(self):
        cfg = PolicyConfig(max_emails_per_day=2)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=2,
        )
        result = engine.evaluate(ctx)
        assert result.context["max_emails_per_day"] == 2
        assert result.context["emails_sent_today"] == 2

    def test_high_value_context_includes_threshold(self):
        cfg = PolicyConfig(human_review_above=400_000)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=400_001,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.context["threshold_paise"] == 400_000

    def test_default_context_includes_emails_sent(self):
        cfg = PolicyConfig(max_emails_per_day=3)
        engine = PolicyEngine(cfg)
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
            emails_sent_today=2,
        )
        result = engine.evaluate(ctx)
        assert result.context["emails_sent_today"] == 2


# ── Engine with no config uses defaults ─────────────────────────────────────

class TestEngineDefaults:
    def test_no_config_uses_defaults(self):
        engine = PolicyEngine()
        assert engine.config.max_auto_payment == 500_000
        assert engine.config.max_emails_per_day == 1
        assert engine.config.required_opt_in is True
        assert engine.config.human_review_above == 500_000

    def test_evaluates_correctly_with_defaults(self):
        engine = PolicyEngine()
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE
