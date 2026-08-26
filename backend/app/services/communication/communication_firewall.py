from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


# ── Enums ───────────────────────────────────────────────────────────────────

class BlockReason(str, enum.Enum):
    NO_CONSENT = "no_consent"
    OPTED_OUT = "opted_out"
    DAILY_LIMIT = "daily_limit"
    TEMPLATE_INVALID = "template_invalid"
    KILL_SWITCH = "kill_switch"


class FirewallAction(str, enum.Enum):
    SEND_EMAIL = "send_email"
    SEND_SMS = "send_sms"
    SEND_WHATSAPP = "send_whatsapp"


# ── Config ──────────────────────────────────────────────────────────────────

APPROVED_TEMPLATES: frozenset[str] = frozenset({
    "PAYMENT_RECOVERY",
    "PAYMENT_FAILURE",
    "PAYMENT_REMINDER",
})


@dataclass(frozen=True)
class CommunicationConfig:
    max_emails_per_day: int = 1
    approved_templates: frozenset[str] = APPROVED_TEMPLATES


# ── Context ─────────────────────────────────────────────────────────────────

@dataclass
class CommunicationContext:
    """Current state at execution time. Not what the AI claims — what the DB says."""
    customer_id: str
    has_consent: bool
    opted_out: bool
    emails_sent_today: int
    template: str
    automation_enabled: bool
    action: FirewallAction = FirewallAction.SEND_EMAIL


# ── Result ──────────────────────────────────────────────────────────────────

@dataclass
class CommunicationResult:
    allowed: bool
    blocked: bool = False
    reason: BlockReason | None = None
    message: str = ""
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "reason": self.reason.value if self.reason else None,
            "message": self.message,
            "decision_id": self.decision_id,
        }


# ── Decision Log Entry ─────────────────────────────────────────────────────

@dataclass
class PolicyDecisionEntry:
    decision_id: str
    action: str
    policy: str
    reason: str
    result: str
    customer_id: str
    timestamp: datetime
    context_snapshot: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "action": self.action,
            "policy": self.policy,
            "reason": self.reason,
            "result": self.result,
            "customer_id": self.customer_id,
            "timestamp": self.timestamp.isoformat(),
            "context_snapshot": self.context_snapshot,
        }


# ── Firewall ────────────────────────────────────────────────────────────────

class CommunicationFirewall:
    """5 checks + kill switch. Every decision is logged.

    Priority order:
      1. kill_switch   — if automation_enabled is False, BLOCK everything
      2. opted_out     — if customer opted out, BLOCK (current state wins)
      3. no_consent    — if no consent, BLOCK
      4. daily_limit   — if emails_sent_today >= limit, BLOCK
      5. template      — if template not in approved set, BLOCK
    """

    def __init__(self, config: CommunicationConfig | None = None) -> None:
        self.config = config or CommunicationConfig()
        self._decisions: list[PolicyDecisionEntry] = []

    @property
    def decisions(self) -> list[PolicyDecisionEntry]:
        return list(self._decisions)

    def evaluate(self, ctx: CommunicationContext) -> CommunicationResult:
        result = self._evaluate(ctx)
        self._log_decision(ctx, result)
        return result

    def _evaluate(self, ctx: CommunicationContext) -> CommunicationResult:
        # Check 1: Kill switch
        if not ctx.automation_enabled:
            return CommunicationResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.KILL_SWITCH,
                message="Automation is disabled — all actions blocked",
            )

        # Check 2: Opted out (current state wins)
        if ctx.opted_out:
            return CommunicationResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.OPTED_OUT,
                message="Customer has opted out of communications",
            )

        # Check 3: No consent
        if not ctx.has_consent:
            return CommunicationResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.NO_CONSENT,
                message="Customer has not provided email consent",
            )

        # Check 4: Daily limit
        if ctx.emails_sent_today >= self.config.max_emails_per_day:
            return CommunicationResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.DAILY_LIMIT,
                message=(
                    f"Daily email limit reached: {ctx.emails_sent_today}/"
                    f"{self.config.max_emails_per_day}"
                ),
            )

        # Check 5: Template validation
        if ctx.template not in self.config.approved_templates:
            return CommunicationResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.TEMPLATE_INVALID,
                message=f"Template '{ctx.template}' is not approved",
            )

        return CommunicationResult(
            allowed=True,
            message="Communication approved",
        )

    def _log_decision(self, ctx: CommunicationContext, result: CommunicationResult) -> None:
        entry = PolicyDecisionEntry(
            decision_id=result.decision_id,
            action=ctx.action.value,
            policy=result.reason.value if result.reason else "none",
            reason=result.message,
            result="BLOCK" if result.blocked else "ALLOW",
            customer_id=ctx.customer_id,
            timestamp=datetime.now(timezone.utc),
            context_snapshot={
                "has_consent": ctx.has_consent,
                "opted_out": ctx.opted_out,
                "emails_sent_today": ctx.emails_sent_today,
                "template": ctx.template,
                "automation_enabled": ctx.automation_enabled,
            },
        )
        self._decisions.append(entry)

    def get_customer_decisions(self, customer_id: str) -> list[PolicyDecisionEntry]:
        return [d for d in self._decisions if d.customer_id == customer_id]

    def get_blocked_decisions(self) -> list[PolicyDecisionEntry]:
        return [d for d in self._decisions if d.result == "BLOCK"]
