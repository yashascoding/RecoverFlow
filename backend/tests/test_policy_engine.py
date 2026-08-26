from app.services.policy.policy_engine import PolicyContext, PolicyEngine, PolicyVerdict


engine = PolicyEngine()

# ₹5,000 = 500,000 paise
THRESHOLD = 500_000


class TestNoConsentRule:
    def test_no_consent_blocks(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "no_consent"
        assert "consent" in result.reason.lower()

    def test_no_consent_blocks_even_if_low_amount(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=1_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "no_consent"

    def test_no_consent_blocks_even_if_not_recovered(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=499_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK

    def test_consent_granted_passes_rule_1(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict != PolicyVerdict.BLOCK or result.rule != "no_consent"


class TestHighValueRule:
    def test_amount_above_5000_triggers_review(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=THRESHOLD + 1,  # ₹5,000.01
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW
        assert result.rule == "high_value"
        assert "5,000" in result.reason

    def test_amount_exactly_5000_is_candidate(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=THRESHOLD,  # ₹5,000 exactly
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE
        assert result.rule == "default"

    def test_amount_below_5000_is_candidate(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=THRESHOLD - 1,  # ₹4,999.99
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE

    def test_high_value_not_reached_without_consent(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=1_000_000,  # ₹10,000
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        # Rule 1 (no_consent) fires first
        assert result.rule == "no_consent"
        assert result.verdict == PolicyVerdict.BLOCK

    def test_amount_7999_triggers_review(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=799_000,  # ₹7,990
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW
        assert result.rule == "high_value"


class TestAlreadyRecoveredRule:
    def test_already_recovered_blocks(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=True,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK
        assert result.rule == "already_recovered"
        assert "already been recovered" in result.reason.lower()

    def test_not_recovered_passes(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.rule != "already_recovered"

    def test_already_recovered_high_value_triggers_review_first(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=1_000_000,  # ₹10,000
            is_already_recovered=True,
        )
        result = engine.evaluate(ctx)
        # Rule 2 (high_value) fires before rule 3 (already_recovered)
        assert result.verdict == PolicyVerdict.HUMAN_REVIEW
        assert result.rule == "high_value"


class TestDefaultRecoveryCandidate:
    def test_happy_path_is_candidate(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=299_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE
        assert result.rule == "default"
        assert "eligible" in result.reason.lower()

    def test_minimal_amount_is_candidate(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=1_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.RECOVERY_CANDIDATE

    def test_to_dict_format(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=299_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        d = result.to_dict()
        assert d["verdict"] == "recovery_candidate"
        assert d["rule"] == "default"
        assert "reason" in d
        assert isinstance(d["context"], dict)


class TestRuleOrdering:
    """Verify rules are evaluated in correct priority order."""

    def test_no_consent_takes_priority_over_high_value(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=1_000_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.rule == "no_consent"

    def test_no_consent_takes_priority_over_recovered(self):
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=True,
        )
        result = engine.evaluate(ctx)
        assert result.rule == "no_consent"

    def test_high_value_takes_priority_over_recovered(self):
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=1_000_000,  # ₹10,000
            is_already_recovered=True,
        )
        result = engine.evaluate(ctx)
        assert result.rule == "high_value"
