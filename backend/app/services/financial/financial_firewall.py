from __future__ import annotations

import enum
from dataclasses import dataclass, field


class BlockReason(str, enum.Enum):
    UNAUTHORIZED_REFUND = "unauthorized_refund"
    PAYMENT_MODIFICATION = "payment_modification"
    HIGH_VALUE_AUTOMATION = "high_value_automation"
    DUPLICATE_RECOVERY = "duplicate_recovery"


@dataclass(frozen=True)
class FirewallConfig:
    max_auto_refund_paise: int = 500_000       # ₹5,000
    max_auto_payment_paise: int = 500_000      # ₹5,000
    allow_payment_modification: bool = False
    require_refund_authorization: bool = True


@dataclass
class FirewallResult:
    allowed: bool
    blocked: bool = False
    reason: BlockReason | None = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "reason": self.reason.value if self.reason else None,
            "message": self.message,
        }


class FinancialFirewall:
    """Hard blocks on financial operations. No exceptions, no overrides.

    Rules:
      1. UNAUTHORIZED_REFUND  — refund amount > max_auto_refund_paise → BLOCK
      2. PAYMENT_MODIFICATION — any mutation of captured payment → BLOCK
      3. HIGH_VALUE_AUTOMATION— auto-recovery amount > max_auto_payment_paise → BLOCK
      4. DUPLICATE_RECOVERY   — recovery attempt already exists for payment → BLOCK
    """

    def __init__(self, config: FirewallConfig | None = None) -> None:
        self.config = config or FirewallConfig()

    def check_refund(
        self,
        amount_paise: int,
        *,
        authorized: bool = False,
        current_status: str = "",
    ) -> FirewallResult:
        """Rule 1: Block unauthorized refunds."""
        if current_status == "refunded":
            return FirewallResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.UNAUTHORIZED_REFUND,
                message="Payment is already refunded",
            )

        if current_status not in ("captured",):
            return FirewallResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.UNAUTHORIZED_REFUND,
                message=f"Cannot refund payment in '{current_status}' state",
            )

        if not authorized and amount_paise > self.config.max_auto_refund_paise:
            return FirewallResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.UNAUTHORIZED_REFUND,
                message=(
                    f"Refund ₹{amount_paise // 100} exceeds auto-refund limit "
                    f"₹{self.config.max_auto_refund_paise // 100} — requires authorization"
                ),
            )

        return FirewallResult(allowed=True, message="Refund approved")

    def check_payment_modification(
        self,
        *,
        current_status: str,
        target_status: str,
    ) -> FirewallResult:
        """Rule 2: Block modification of payments in non-modifiable states."""
        if not self.config.allow_payment_modification:
            immutable = {"captured", "refunded", "recovered"}
            if current_status in immutable:
                return FirewallResult(
                    allowed=False,
                    blocked=True,
                    reason=BlockReason.PAYMENT_MODIFICATION,
                    message=(
                        f"Cannot modify payment in '{current_status}' state — "
                        f"status is immutable"
                    ),
                )

        return FirewallResult(allowed=True, message="Modification allowed")

    def check_auto_recovery(
        self,
        amount_paise: int,
        *,
        existing_attempts: int = 0,
    ) -> FirewallResult:
        """Rule 3 + 4: Block high-value automation and duplicate recovery."""
        if amount_paise > self.config.max_auto_payment_paise:
            return FirewallResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.HIGH_VALUE_AUTOMATION,
                message=(
                    f"Auto-recovery ₹{amount_paise // 100} exceeds limit "
                    f"₹{self.config.max_auto_payment_paise // 100}"
                ),
            )

        if existing_attempts > 0:
            return FirewallResult(
                allowed=False,
                blocked=True,
                reason=BlockReason.DUPLICATE_RECOVERY,
                message=(
                    f"Recovery already attempted {existing_attempts} time(s) for this payment"
                ),
            )

        return FirewallResult(allowed=True, message="Auto-recovery approved")
