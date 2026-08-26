import pytest

from app.services.communication.communication_firewall import (
    APPROVED_TEMPLATES,
    BlockReason,
    CommunicationConfig,
    CommunicationContext,
    CommunicationFirewall,
    CommunicationResult,
    FirewallAction,
    PolicyDecisionEntry,
)


def _ctx(**overrides) -> CommunicationContext:
    defaults = dict(
        customer_id="cust_001",
        has_consent=True,
        opted_out=False,
        emails_sent_today=0,
        template="PAYMENT_RECOVERY",
        automation_enabled=True,
        action=FirewallAction.SEND_EMAIL,
    )
    defaults.update(overrides)
    return CommunicationContext(**defaults)


# ── Check 1: Kill switch ────────────────────────────────────────────────────

class TestKillSwitch:
    def test_blocks_when_disabled(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(automation_enabled=False))
        assert result.blocked is True
        assert result.allowed is False
        assert result.reason == BlockReason.KILL_SWITCH
        assert "disabled" in result.message.lower()

    def test_allows_when_enabled(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(automation_enabled=True))
        assert result.allowed is True

    def test_kill_switch_overrides_everything(self):
        """Even with consent + valid template + under limit, kill switch blocks."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(
            automation_enabled=False,
            has_consent=True,
            opted_out=False,
            emails_sent_today=0,
            template="PAYMENT_RECOVERY",
        ))
        assert result.blocked is True
        assert result.reason == BlockReason.KILL_SWITCH

    def test_kill_switch_checked_first(self):
        """Kill switch fires before any other check."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(
            automation_enabled=False,
            has_consent=False,
            opted_out=True,
            emails_sent_today=999,
            template="INVALID",
        ))
        assert result.reason == BlockReason.KILL_SWITCH


# ── Check 2: Opted out ─────────────────────────────────────────────────────

class TestOptedOut:
    def test_blocks_when_opted_out(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(opted_out=True))
        assert result.blocked is True
        assert result.reason == BlockReason.OPTED_OUT
        assert "opted out" in result.message.lower()

    def test_allows_when_not_opted_out(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(opted_out=False))
        assert result.allowed is True

    def test_opted_out_overrides_consent(self):
        """Even with consent, opted out blocks."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=True, opted_out=True))
        assert result.reason == BlockReason.OPTED_OUT

    def test_current_state_wins(self):
        """AI can't claim 'they opted in yesterday' — current state matters."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=True, opted_out=True))
        assert result.blocked is True
        assert result.reason == BlockReason.OPTED_OUT


# ── Check 3: No consent ────────────────────────────────────────────────────

class TestNoConsent:
    def test_blocks_when_no_consent(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False))
        assert result.blocked is True
        assert result.reason == BlockReason.NO_CONSENT
        assert "consent" in result.message.lower()

    def test_allows_when_consent_given(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=True))
        assert result.allowed is True

    def test_consent_required_even_with_valid_template(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, template="PAYMENT_RECOVERY"))
        assert result.reason == BlockReason.NO_CONSENT


# ── Check 4: Daily limit ───────────────────────────────────────────────────

class TestDailyLimit:
    def test_blocks_when_limit_reached(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(emails_sent_today=1))
        assert result.blocked is True
        assert result.reason == BlockReason.DAILY_LIMIT
        assert "1/1" in result.message

    def test_allows_when_under_limit(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(emails_sent_today=0))
        assert result.allowed is True

    def test_custom_limit(self):
        fw = CommunicationFirewall(CommunicationConfig(max_emails_per_day=3))
        result = fw.evaluate(_ctx(emails_sent_today=3))
        assert result.blocked is True
        assert "3/3" in result.message

    def test_custom_limit_under(self):
        fw = CommunicationFirewall(CommunicationConfig(max_emails_per_day=3))
        result = fw.evaluate(_ctx(emails_sent_today=2))
        assert result.allowed is True

    def test_limit_of_zero_blocks_all(self):
        fw = CommunicationFirewall(CommunicationConfig(max_emails_per_day=0))
        result = fw.evaluate(_ctx(emails_sent_today=0))
        assert result.blocked is True
        assert result.reason == BlockReason.DAILY_LIMIT


# ── Check 5: Template validation ───────────────────────────────────────────

class TestTemplateValidation:
    def test_approved_templates_allow(self):
        fw = CommunicationFirewall()
        for template in APPROVED_TEMPLATES:
            result = fw.evaluate(_ctx(template=template))
            assert result.allowed is True, f"Template {template} should be approved"

    def test_unknown_template_blocks(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(template="random_custom_template"))
        assert result.blocked is True
        assert result.reason == BlockReason.TEMPLATE_INVALID
        assert "random_custom_template" in result.message

    def test_empty_template_blocks(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(template=""))
        assert result.blocked is True
        assert result.reason == BlockReason.TEMPLATE_INVALID

    def test_custom_approved_templates(self):
        fw = CommunicationFirewall(CommunicationConfig(
            approved_templates=frozenset({"CUSTOM_1", "CUSTOM_2"})
        ))
        assert fw.evaluate(_ctx(template="CUSTOM_1")).allowed
        assert fw.evaluate(_ctx(template="CUSTOM_2")).allowed
        assert fw.evaluate(_ctx(template="PAYMENT_RECOVERY")).blocked


# ── Rule priority ordering ──────────────────────────────────────────────────

class TestRuleOrdering:
    def test_kill_switch_before_opted_out(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(automation_enabled=False, opted_out=True))
        assert result.reason == BlockReason.KILL_SWITCH

    def test_opted_out_before_no_consent(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, opted_out=True))
        assert result.reason == BlockReason.OPTED_OUT

    def test_no_consent_before_daily_limit(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, emails_sent_today=5))
        assert result.reason == BlockReason.NO_CONSENT

    def test_daily_limit_before_template(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(emails_sent_today=1, template="INVALID"))
        assert result.reason == BlockReason.DAILY_LIMIT

    def test_template_last(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(template="INVALID"))
        assert result.reason == BlockReason.TEMPLATE_INVALID


# ── Attack scenarios ────────────────────────────────────────────────────────

class TestAttackScenarios:
    def test_attack_ignore_policy(self):
        """AI says 'ignore policy, send anyway' — firewall doesn't care about text."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False))
        assert result.blocked is True

    def test_attack_implied_consent(self):
        """AI claims consent is 'probably implied' — DB says no consent."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False))
        assert result.blocked is True
        assert result.reason == BlockReason.NO_CONSENT

    def test_attack_urgency_manipulation(self):
        """AI says 'customer will churn if we don't send now' — still blocked."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, opted_out=True))
        assert result.blocked is True

    def test_attack_override_kill_switch(self):
        """AI can't override kill switch by claiming urgency."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(
            automation_enabled=False,
            has_consent=True,
            opted_out=False,
            emails_sent_today=0,
            template="PAYMENT_RECOVERY",
        ))
        assert result.reason == BlockReason.KILL_SWITCH

    def test_attack_fake_template(self):
        """AI uses an unapproved template — blocked."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(template="SPECIAL_URGENT_EMAIL"))
        assert result.blocked is True
        assert result.reason == BlockReason.TEMPLATE_INVALID

    def test_database_state_wins_over_ai_claims(self):
        """Architectural principle: DB + deterministic rules decide, not LLM."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False))
        assert result.blocked is True


# ── Consent revocation at execution time ────────────────────────────────────

class TestConsentRevocation:
    def test_revoked_consent_blocks(self):
        """Customer opted in at 10:00, revoked at 10:02, AI sends at 10:03."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, opted_out=True))
        assert result.blocked is True
        assert result.reason == BlockReason.OPTED_OUT

    def test_consent_removed_blocks(self):
        """Opted in earlier, consent now False."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False, opted_out=False))
        assert result.blocked is True
        assert result.reason == BlockReason.NO_CONSENT

    def test_consent_restored_allows(self):
        """Was revoked, now restored."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=True, opted_out=False))
        assert result.allowed is True

    def test_opted_out_overrides_prior_consent(self):
        """AI says 'they opted in yesterday' — but current state is opted out."""
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=True, opted_out=True))
        assert result.reason == BlockReason.OPTED_OUT


# ── Decision logging ────────────────────────────────────────────────────────

class TestDecisionLogging:
    def test_every_evaluation_logged(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx())
        fw.evaluate(_ctx(has_consent=False))
        assert len(fw.decisions) == 2

    def test_blocked_decision_logged(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(has_consent=False))
        assert len(fw.decisions) == 1
        entry = fw.decisions[0]
        assert entry.result == "BLOCK"
        assert entry.policy == "no_consent"
        assert entry.customer_id == "cust_001"
        assert entry.action == "send_email"

    def test_allowed_decision_logged(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx())
        entry = fw.decisions[0]
        assert entry.result == "ALLOW"
        assert entry.policy == "none"

    def test_decision_has_timestamp(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx())
        assert fw.decisions[0].timestamp is not None

    def test_decision_has_context_snapshot(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx(emails_sent_today=2))
        snapshot = fw.decisions[0].context_snapshot
        assert snapshot["emails_sent_today"] == 2
        assert snapshot["has_consent"] is True
        assert snapshot["template"] == "PAYMENT_RECOVERY"

    def test_decision_has_unique_id(self):
        fw = CommunicationFirewall()
        r1 = fw.evaluate(_ctx())
        r2 = fw.evaluate(_ctx(has_consent=False))
        assert r1.decision_id != r2.decision_id

    def test_get_customer_decisions(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx(customer_id="c1"))
        fw.evaluate(_ctx(customer_id="c2", has_consent=False))
        fw.evaluate(_ctx(customer_id="c1", has_consent=False))
        c1 = fw.get_customer_decisions("c1")
        assert len(c1) == 2
        c2 = fw.get_customer_decisions("c2")
        assert len(c2) == 1

    def test_get_blocked_decisions(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx())
        fw.evaluate(_ctx(has_consent=False))
        fw.evaluate(_ctx(opted_out=True))
        blocked = fw.get_blocked_decisions()
        assert len(blocked) == 2
        assert all(d.result == "BLOCK" for d in blocked)

    def test_decision_to_dict(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx())
        d = fw.decisions[0].to_dict()
        assert "decision_id" in d
        assert "timestamp" in d
        assert d["result"] == "ALLOW"


# ── Audit trail ─────────────────────────────────────────────────────────────

class TestAuditTrail:
    def test_full_audit_record_for_blocked_action(self):
        fw = CommunicationFirewall()
        result = fw.evaluate(_ctx(
            customer_id="cust_42",
            has_consent=False,
            template="PAYMENT_RECOVERY",
        ))
        entry = fw.decisions[0]

        assert entry.customer_id == "cust_42"
        assert entry.action == "send_email"
        assert entry.policy == "no_consent"
        assert entry.result == "BLOCK"
        assert entry.reason == "Customer has not provided email consent"
        assert entry.timestamp is not None

    def test_audit_trail_shows_chain(self):
        """You can reconstruct: WHO → WHAT → WHY → POLICY → WHEN → RESULT."""
        fw = CommunicationFirewall()
        fw.evaluate(_ctx(customer_id="c1", automation_enabled=False))
        fw.evaluate(_ctx(customer_id="c1", has_consent=False))
        fw.evaluate(_ctx(customer_id="c1"))

        entries = fw.get_customer_decisions("c1")
        reasons = [e.policy for e in entries]
        assert reasons == ["kill_switch", "no_consent", "none"]
        results = [e.result for e in entries]
        assert results == ["BLOCK", "BLOCK", "ALLOW"]

    def test_multiple_customers_independent(self):
        fw = CommunicationFirewall()
        fw.evaluate(_ctx(customer_id="c1", has_consent=False))
        fw.evaluate(_ctx(customer_id="c2"))
        assert len(fw.get_customer_decisions("c1")) == 1
        assert len(fw.get_customer_decisions("c2")) == 1
        assert fw.get_customer_decisions("c1")[0].result == "BLOCK"
        assert fw.get_customer_decisions("c2")[0].result == "ALLOW"
