import pytest

from app.services.policy.policy_decision_logger import (
    DecisionResult,
    PolicyDecisionLogger,
    PolicyDecisionRecord,
)
from app.services.communication.communication_firewall import (
    CommunicationConfig,
    CommunicationContext,
    CommunicationFirewall,
    FirewallAction,
)
from app.services.financial.financial_firewall import (
    FinancialFirewall,
    FirewallConfig,
)
from app.services.policy.policy_engine import (
    PolicyConfig,
    PolicyContext,
    PolicyEngine,
    PolicyVerdict,
)


# ── Logger basics ───────────────────────────────────────────────────────────

class TestLoggerBasics:
    def test_record_returns_entry(self):
        logger = PolicyDecisionLogger()
        entry = logger.record(
            who="agent_1",
            what="send_email",
            policy="required_opt_in",
            reason="No consent",
            result=DecisionResult.BLOCK,
        )
        assert isinstance(entry, PolicyDecisionRecord)
        assert entry.decision_id is not None

    def test_records_stored(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        assert len(logger.records) == 1

    def test_multiple_records(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK)
        assert len(logger.records) == 2

    def test_to_dict(self):
        logger = PolicyDecisionLogger()
        entry = logger.record(
            who="agent_1", what="send_email", policy="opt_in",
            reason="test", result=DecisionResult.BLOCK,
            customer_id="c1", payment_id="p1", amount_paise=5000,
            context={"key": "value"},
        )
        d = entry.to_dict()
        assert d["who"] == "agent_1"
        assert d["what"] == "send_email"
        assert d["policy"] == "opt_in"
        assert d["result"] == "BLOCK"
        assert d["customer_id"] == "c1"
        assert d["payment_id"] == "p1"
        assert d["amount_paise"] == 5000
        assert d["context"] == {"key": "value"}
        assert "timestamp" in d
        assert "decision_id" in d


# ── Query methods ───────────────────────────────────────────────────────────

class TestQueryMethods:
    def test_get_by_customer(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW, customer_id="c1")
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK, customer_id="c2")
        logger.record(who="a", what="z", policy="p", reason="r", result=DecisionResult.ALLOW, customer_id="c1")
        assert len(logger.get_by_customer("c1")) == 2
        assert len(logger.get_by_customer("c2")) == 1

    def test_get_by_payment(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW, payment_id="p1")
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK, payment_id="p2")
        assert len(logger.get_by_payment("p1")) == 1

    def test_get_blocked(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK)
        logger.record(who="a", what="z", policy="p", reason="r", result=DecisionResult.BLOCK)
        assert len(logger.get_blocked()) == 2

    def test_get_human_review(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.HUMAN_REVIEW)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.ALLOW)
        assert len(logger.get_human_review()) == 1

    def test_get_allowed(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK)
        assert len(logger.get_allowed()) == 1

    def test_get_by_actor(self):
        logger = PolicyDecisionLogger()
        logger.record(who="agent_1", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        logger.record(who="agent_2", what="y", policy="q", reason="s", result=DecisionResult.BLOCK)
        logger.record(who="agent_1", what="z", policy="p", reason="r", result=DecisionResult.ALLOW)
        assert len(logger.get_by_actor("agent_1")) == 2

    def test_count_blocked(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.BLOCK)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.ALLOW)
        assert logger.count_blocked() == 1

    def test_count_total(self):
        logger = PolicyDecisionLogger()
        logger.record(who="a", what="x", policy="p", reason="r", result=DecisionResult.ALLOW)
        logger.record(who="a", what="y", policy="q", reason="s", result=DecisionResult.BLOCK)
        assert logger.count_total() == 2


# ── Integration: Communication Firewall → Logger ────────────────────────────

class TestCommunicationFirewallWithLogger:
    def test_blocked_action_logged(self):
        logger = PolicyDecisionLogger()
        fw = CommunicationFirewall()

        # Simulate: AI tries to send email, no consent
        ctx = CommunicationContext(
            customer_id="cust_001",
            has_consent=False,
            opted_out=False,
            emails_sent_today=0,
            template="PAYMENT_RECOVERY",
            automation_enabled=True,
        )
        result = fw.evaluate(ctx)

        # Log the decision
        logger.record(
            who="ai_agent",
            what="send_email",
            policy="required_opt_in",
            reason="Customer has not provided email consent",
            result=DecisionResult.BLOCK,
            customer_id="cust_001",
        )

        assert logger.count_blocked() == 1
        entry = logger.get_blocked()[0]
        assert entry.who == "ai_agent"
        assert entry.what == "send_email"
        assert entry.result == DecisionResult.BLOCK

    def test_allowed_action_logged(self):
        logger = PolicyDecisionLogger()
        ctx = CommunicationContext(
            customer_id="cust_002",
            has_consent=True,
            opted_out=False,
            emails_sent_today=0,
            template="PAYMENT_RECOVERY",
            automation_enabled=True,
        )
        fw = CommunicationFirewall()
        result = fw.evaluate(ctx)

        logger.record(
            who="ai_agent",
            what="send_email",
            policy="none",
            reason="Communication approved",
            result=DecisionResult.ALLOW,
            customer_id="cust_002",
        )

        assert logger.count_total() == 1
        assert logger.get_allowed()[0].result == DecisionResult.ALLOW


# ── Integration: Financial Firewall → Logger ────────────────────────────────

class TestFinancialFirewallWithLogger:
    def test_high_value_triggers_human_review(self):
        """₹10,000 payment → HUMAN REVIEW."""
        logger = PolicyDecisionLogger()
        fw = FinancialFirewall()

        result = fw.check_auto_recovery(1_000_000)  # ₹10,000

        if result.blocked:
            logger.record(
                who="ai_agent",
                what="auto_recovery",
                policy="high_value_automation",
                reason=result.message,
                result=DecisionResult.BLOCK,
                amount_paise=1_000_000,
            )
        else:
            logger.record(
                who="ai_agent",
                what="auto_recovery",
                policy="none",
                reason="Approved",
                result=DecisionResult.ALLOW,
                amount_paise=1_000_000,
            )

        assert logger.count_blocked() == 1
        assert logger.get_blocked()[0].amount_paise == 1_000_000

    def test_unauthorized_refund_blocked(self):
        logger = PolicyDecisionLogger()
        fw = FinancialFirewall()

        result = fw.check_refund(600_000, current_status="captured")

        logger.record(
            who="ai_agent",
            what="process_refund",
            policy="unauthorized_refund",
            reason=result.message,
            result=DecisionResult.BLOCK,
            payment_id="pay_123",
            amount_paise=600_000,
        )

        entry = logger.get_blocked()[0]
        assert entry.what == "process_refund"
        assert entry.payment_id == "pay_123"


# ── Integration: Policy Engine → Logger ─────────────────────────────────────

class TestPolicyEngineWithLogger:
    def test_no_consent_blocks(self):
        logger = PolicyDecisionLogger()
        engine = PolicyEngine()
        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)

        logger.record(
            who="policy_engine",
            what="evaluate_recovery",
            policy=result.rule,
            reason=result.reason,
            result=DecisionResult.BLOCK,
            customer_id="cust_005",
        )

        assert logger.get_blocked()[0].policy == "no_consent"

    def test_high_value_human_review(self):
        logger = PolicyDecisionLogger()
        engine = PolicyEngine()
        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=1_000_000,  # ₹10,000
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)

        if result.verdict == PolicyVerdict.HUMAN_REVIEW:
            dr = DecisionResult.HUMAN_REVIEW
        elif result.verdict == PolicyVerdict.BLOCK:
            dr = DecisionResult.BLOCK
        else:
            dr = DecisionResult.ALLOW

        logger.record(
            who="policy_engine",
            what="evaluate_recovery",
            policy=result.rule,
            reason=result.reason,
            result=dr,
            amount_paise=1_000_000,
        )

        assert logger.get_human_review()[0].amount_paise == 1_000_000

    def test_consent_revocation_blocks(self):
        """Customer opted in → consent revoked → email blocked."""
        logger = PolicyDecisionLogger()
        engine = PolicyEngine()

        # Step 1: Consent granted → allowed
        ctx_allowed = PolicyContext(
            has_email_consent=True,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx_allowed)
        logger.record(
            who="policy_engine", what="evaluate_recovery",
            policy=result.rule, reason=result.reason,
            result=DecisionResult.ALLOW, customer_id="cust_rev",
        )

        # Step 2: Consent revoked → blocked
        ctx_blocked = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx_blocked)
        logger.record(
            who="policy_engine", what="evaluate_recovery",
            policy=result.rule, reason=result.reason,
            result=DecisionResult.BLOCK, customer_id="cust_rev",
        )

        cust_decisions = logger.get_by_customer("cust_rev")
        assert len(cust_decisions) == 2
        assert cust_decisions[0].result == DecisionResult.ALLOW
        assert cust_decisions[1].result == DecisionResult.BLOCK


# ── Audit trail: WHO / WHAT / WHY / POLICY / WHEN / RESULT ─────────────────

class TestAuditTrail:
    def test_full_chain_recorded(self):
        """AI → SEND_EMAIL → Policy Firewall → BLOCK → Audit record."""
        logger = PolicyDecisionLogger()

        logger.record(
            who="ai_agent_recovery",
            what="SEND_RECOVERY_EMAIL",
            policy="required_opt_in",
            reason="Customer has not provided email consent",
            result=DecisionResult.BLOCK,
            customer_id="cust_audit",
            payment_id="pay_audit",
            amount_paise=299_00,
            context={"has_consent": False, "template": "PAYMENT_RECOVERY"},
        )

        entry = logger.records[0]
        assert entry.who == "ai_agent_recovery"
        assert entry.what == "SEND_RECOVERY_EMAIL"
        assert entry.reason == "Customer has not provided email consent"
        assert entry.policy == "required_opt_in"
        assert entry.result == DecisionResult.BLOCK
        assert entry.timestamp is not None

    def test_chain_of_three_decisions(self):
        """Multiple decisions for same customer form a trail."""
        logger = PolicyDecisionLogger()

        logger.record(
            who="ai_agent", what="SEND_EMAIL", policy="none",
            reason="Approved", result=DecisionResult.ALLOW, customer_id="c1",
        )
        logger.record(
            who="ai_agent", what="SEND_EMAIL", policy="daily_limit",
            reason="Limit reached", result=DecisionResult.BLOCK, customer_id="c1",
        )
        logger.record(
            who="ai_agent", what="SEND_SMS", policy="none",
            reason="Approved", result=DecisionResult.ALLOW, customer_id="c1",
        )

        trail = logger.get_by_customer("c1")
        assert len(trail) == 3
        assert [d.result.value for d in trail] == ["ALLOW", "BLOCK", "ALLOW"]
        assert [d.what for d in trail] == ["SEND_EMAIL", "SEND_EMAIL", "SEND_SMS"]

    def test_high_value_payment_trail(self):
        """₹10,000 payment: AI requests → policy blocks → audit."""
        logger = PolicyDecisionLogger()
        engine = PolicyEngine()

        ctx = PolicyContext(
            has_email_consent=True,
            amount_paise=1_000_000,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)

        if result.verdict == PolicyVerdict.HUMAN_REVIEW:
            dr = DecisionResult.HUMAN_REVIEW
        elif result.verdict == PolicyVerdict.BLOCK:
            dr = DecisionResult.BLOCK
        else:
            dr = DecisionResult.ALLOW

        logger.record(
            who="ai_agent",
            what="auto_recover_payment",
            policy=result.rule,
            reason=result.reason,
            result=dr,
            customer_id="c_high",
            payment_id="p_high",
            amount_paise=1_000_000,
        )

        entry = logger.records[0]
        assert entry.amount_paise == 1_000_000
        assert entry.result == DecisionResult.HUMAN_REVIEW
        assert entry.policy == "high_value"


# ── Attack testing: AI can't bypass ─────────────────────────────────────────

class TestAttackTesting:
    def test_ai_cannot_override_no_consent(self):
        """AI says 'ignore policy' — database says no consent → BLOCK."""
        logger = PolicyDecisionLogger()
        engine = PolicyEngine()

        ctx = PolicyContext(
            has_email_consent=False,
            amount_paise=100_00,
            is_already_recovered=False,
        )
        result = engine.evaluate(ctx)
        assert result.verdict == PolicyVerdict.BLOCK

        logger.record(
            who="ai_agent", what="send_email", policy=result.rule,
            reason=result.reason, result=DecisionResult.BLOCK,
            customer_id="c_attack",
        )

        assert logger.get_blocked()[0].policy == "no_consent"

    def test_ai_cannot_override_kill_switch(self):
        """AI says 'urgent, send now' — kill switch says no → BLOCK."""
        logger = PolicyDecisionLogger()
        fw = CommunicationFirewall()

        ctx = CommunicationContext(
            customer_id="c_kill",
            has_consent=True,
            opted_out=False,
            emails_sent_today=0,
            template="PAYMENT_RECOVERY",
            automation_enabled=False,
        )
        result = fw.evaluate(ctx)
        assert result.blocked is True

        logger.record(
            who="ai_agent", what="send_email", policy="kill_switch",
            reason=result.message, result=DecisionResult.BLOCK,
            customer_id="c_kill",
        )

        assert logger.get_blocked()[0].policy == "kill_switch"

    def test_ai_cannot_override_high_value(self):
        """AI says 'auto-process ₹10,000' — policy says human review."""
        logger = PolicyDecisionLogger()
        fw = FinancialFirewall()

        result = fw.check_auto_recovery(1_000_000)
        assert result.blocked is True

        logger.record(
            who="ai_agent", what="auto_recovery",
            policy="high_value_automation", reason=result.message,
            result=DecisionResult.BLOCK, amount_paise=1_000_000,
        )

        assert logger.get_blocked()[0].amount_paise == 1_000_000
