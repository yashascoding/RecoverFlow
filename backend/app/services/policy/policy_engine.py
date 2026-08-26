from __future__ import annotations

import enum
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger(__name__)


class PolicyVerdict(str, enum.Enum):
    RECOVERY_CANDIDATE = "recovery_candidate"
    BLOCK = "block"
    HUMAN_REVIEW = "human_review"


@dataclass
class PolicyContext:
    has_email_consent: bool
    amount_paise: int
    is_already_recovered: bool
    failure_reason: str | None = None
    customer_status: str | None = None
    attempt_count: int = 0


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


class PolicyEngine:
    """Deterministic policy engine with ordered rules.

    Rules are evaluated top-to-bottom. First match wins.
    """

    HIGH_VALUE_THRESHOLD_PAISE = 500_000  # ₹5,000

    def evaluate(self, ctx: PolicyContext) -> PolicyResult:
        # Rule 1: No consent → BLOCK
        if not ctx.has_email_consent:
            return PolicyResult(
                verdict=PolicyVerdict.BLOCK,
                reason="Customer has not granted email consent",
                rule="no_consent",
                context={"has_email_consent": False},
            )

        # Rule 2: Amount > ₹5,000 → HUMAN REVIEW
        if ctx.amount_paise > self.HIGH_VALUE_THRESHOLD_PAISE:
            return PolicyResult(
                verdict=PolicyVerdict.HUMAN_REVIEW,
                reason=f"Payment amount ₹{ctx.amount_paise // 100} exceeds ₹5,000 threshold",
                rule="high_value",
                context={"amount_paise": ctx.amount_paise, "threshold_paise": self.HIGH_VALUE_THRESHOLD_PAISE},
            )

        # Rule 3: Already recovered → BLOCK
        if ctx.is_already_recovered:
            return PolicyResult(
                verdict=PolicyVerdict.BLOCK,
                reason="Payment has already been recovered",
                rule="already_recovered",
                context={"is_already_recovered": True},
            )

        # Rule 4: Otherwise → RECOVERY CANDIDATE
        return PolicyResult(
            verdict=PolicyVerdict.RECOVERY_CANDIDATE,
            reason="Payment is eligible for automated recovery",
            rule="default",
            context={
                "has_email_consent": ctx.has_email_consent,
                "amount_paise": ctx.amount_paise,
                "is_already_recovered": ctx.is_already_recovered,
            },
        )
