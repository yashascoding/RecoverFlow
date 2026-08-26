from __future__ import annotations

import enum
from dataclasses import dataclass, field


class FailureCategory(str, enum.Enum):
    UPI_TIMEOUT = "upi_timeout"
    BANK_DECLINED = "bank_declined"
    NETWORK_ERROR = "network_error"
    GATEWAY_ERROR = "gateway_error"
    FRAUD_CHECK = "fraud_check"
    UNKNOWN = "unknown"


class RecoveryStrategy(str, enum.Enum):
    INSTANT_RETRY = "instant_retry"
    DELAYED_RETRY = "delayed_retry"
    ALTERNATE_CHANNEL = "alternate_channel"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    BLOCK_RECOVERY = "block_recovery"


@dataclass
class DiagnosisResult:
    category: FailureCategory
    strategy: RecoveryStrategy
    reason: str
    retry_after_seconds: int | None = None
    max_retries: int | None = None
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "strategy": self.strategy.value,
            "reason": self.reason,
            "retry_after_seconds": self.retry_after_seconds,
            "max_retries": self.max_retries,
            "context": self.context,
        }


# ── Keyword → Category mapping ───────────────────────────────────────────
_FAILURE_PATTERNS: list[tuple[list[str], FailureCategory]] = [
    (["timeout", "timed out", "upi timeout", "session expired"], FailureCategory.UPI_TIMEOUT),
    (["declined", "rejected", "insufficient funds", "blocked by issuer", "do not honor", "card expired"], FailureCategory.BANK_DECLINED),
    (["network", "connection reset", "connection refused", "dns resolution", "socket timeout"], FailureCategory.NETWORK_ERROR),
    (["gateway", "bad gateway", "service unavailable", "502", "503", "504"], FailureCategory.GATEWAY_ERROR),
    (["fraud", "suspicious", "velocity check", "device binding", "risk assessment", "3ds"], FailureCategory.FRAUD_CHECK),
]

# ── Category → Strategy mapping ──────────────────────────────────────────
_STRATEGY_MAP: dict[FailureCategory, tuple[RecoveryStrategy, str, int | None, int | None]] = {
    FailureCategory.UPI_TIMEOUT: (
        RecoveryStrategy.INSTANT_RETRY,
        "UPI timeout is usually transient — retry immediately",
        0,
        3,
    ),
    FailureCategory.BANK_DECLINED: (
        RecoveryStrategy.DELAYED_RETRY,
        "Bank declined — retry after delay or suggest alternate payment method",
        3600,
        2,
    ),
    FailureCategory.NETWORK_ERROR: (
        RecoveryStrategy.INSTANT_RETRY,
        "Network error is transient — retry immediately",
        0,
        3,
    ),
    FailureCategory.GATEWAY_ERROR: (
        RecoveryStrategy.DELAYED_RETRY,
        "Gateway error — wait for service recovery then retry",
        1800,
        2,
    ),
    FailureCategory.FRAUD_CHECK: (
        RecoveryStrategy.ESCALATE_TO_HUMAN,
        "Fraud check triggered — requires manual review",
        None,
        0,
    ),
    FailureCategory.UNKNOWN: (
        RecoveryStrategy.ALTERNATE_CHANNEL,
        "Unknown failure — try alternate recovery channel",
        None,
        1,
    ),
}


class FailureDiagnosisEngine:
    """Maps raw failure reasons to recovery strategies."""

    def diagnose(self, failure_reason: str | None) -> DiagnosisResult:
        if not failure_reason:
            return self._make_result(FailureCategory.UNKNOWN, "No failure reason provided")

        reason_lower = failure_reason.lower()

        for patterns, category in _FAILURE_PATTERNS:
            if any(p in reason_lower for p in patterns):
                return self._make_result(category, failure_reason)

        return self._make_result(FailureCategory.UNKNOWN, failure_reason)

    def _make_result(self, category: FailureCategory, raw_reason: str) -> DiagnosisResult:
        strategy, reason, retry_after, max_retries = _STRATEGY_MAP[category]
        return DiagnosisResult(
            category=category,
            strategy=strategy,
            reason=reason,
            retry_after_seconds=retry_after,
            max_retries=max_retries,
            context={"raw_failure_reason": raw_reason},
        )
