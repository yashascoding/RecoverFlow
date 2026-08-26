from __future__ import annotations

import enum
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Configuration ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PolicyConfig:
    """Tunable policy thresholds. All amounts in paise."""

    max_auto_payment: int = 500_000       # ₹5,000 — above this → human review
    max_emails_per_day: int = 1           # per customer per day
    required_opt_in: bool = True          # must have email consent
    human_review_above: int = 500_000     # ₹5,000 — alias for max_auto_payment


# ── Enums ───────────────────────────────────────────────────────────────────

class PolicyVerdict(str, enum.Enum):
    RECOVERY_CANDIDATE = "recovery_candidate"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"


# ── Context / Result ────────────────────────────────────────────────────────

@dataclass
class PolicyContext:
    has_email_consent: bool
    amount_paise: int
    is_already_recovered: bool
    failure_reason: str | None = None
    customer_status: str | None = None
    attempt_count: int = 0
    emails_sent_today: int = 0


@dataclass
class PolicyResult:
    verdict: PolicyVerdict
    reason: str
    rule: str
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "reason": self.reason,
            "rule": self.rule,
            "context": self.context,
        }


# ── Engine ──────────────────────────────────────────────────────────────────

class PolicyEngine:
    """Deterministic policy engine with ordered rules.

    Rules are evaluated top-to-bottom. First match wins.

    Priority order:
      1. no_consent       — BLOCK if required_opt_in and no consent
      2. daily_limit      — BLOCK if max_emails_per_day reached
      3. high_value       — HUMAN_REVIEW if amount > human_review_above
      4. already_recovered — BLOCK
      5. default          — RECOVERY_CANDIDATE
    """

    def __init__(self, config: PolicyConfig | None = None) -> None:
        self.config = config or PolicyConfig()

    def evaluate(self, ctx: PolicyContext) -> PolicyResult:
        cfg = self.config

        # Rule 1: No consent → BLOCK (when opt-in is required)
        if cfg.required_opt_in and not ctx.has_email_consent:
            return PolicyResult(
                verdict=PolicyVerdict.BLOCK,
                reason="Customer has not granted email consent",
                rule="no_consent",
                context={"has_email_consent": False, "required_opt_in": True},
            )

        # Rule 2: Daily email limit reached → BLOCK
        if ctx.emails_sent_today >= cfg.max_emails_per_day:
            return PolicyResult(
                verdict=PolicyVerdict.BLOCK,
                reason=(
                    f"Daily email limit reached: {ctx.emails_sent_today}/{cfg.max_emails_per_day} "
                    f"emails sent today"
                ),
                rule="daily_limit",
                context={
                    "emails_sent_today": ctx.emails_sent_today,
                    "max_emails_per_day": cfg.max_emails_per_day,
                },
            )

        # Rule 3: Amount above human_review_above → HUMAN_REVIEW
        if ctx.amount_paise > cfg.human_review_above:
            threshold_rupees = cfg.human_review_above // 100
            return PolicyResult(
                verdict=PolicyVerdict.HUMAN_REVIEW,
                reason=(
                    f"Payment amount ₹{ctx.amount_paise // 100} exceeds "
                    f"₹{threshold_rupees:,} threshold"
                ),
                rule="high_value",
                context={
                    "amount_paise": ctx.amount_paise,
                    "threshold_paise": cfg.human_review_above,
                },
            )

        # Rule 4: Already recovered → BLOCK
        if ctx.is_already_recovered:
            return PolicyResult(
                verdict=PolicyVerdict.BLOCK,
                reason="Payment has already been recovered",
                rule="already_recovered",
                context={"is_already_recovered": True},
            )

        # Rule 5: Otherwise → RECOVERY CANDIDATE
        return PolicyResult(
            verdict=PolicyVerdict.RECOVERY_CANDIDATE,
            reason="Payment is eligible for automated recovery",
            rule="default",
            context={
                "has_email_consent": ctx.has_email_consent,
                "amount_paise": ctx.amount_paise,
                "is_already_recovered": ctx.is_already_recovered,
                "emails_sent_today": ctx.emails_sent_today,
            },
        )
