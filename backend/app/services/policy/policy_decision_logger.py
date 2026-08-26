from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


class DecisionResult(str, enum.Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    HUMAN_REVIEW = "HUMAN_REVIEW"


@dataclass
class PolicyDecisionRecord:
    """Single audit record for any policy decision."""

    who: str                                  # agent_id, system, manual
    what: str                                 # action attempted
    policy: str                               # which policy fired
    reason: str                               # human-readable explanation
    result: DecisionResult
    decision_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    customer_id: str | None = None
    payment_id: str | None = None
    amount_paise: int | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "who": self.who,
            "what": self.what,
            "policy": self.policy,
            "reason": self.reason,
            "result": self.result.value,
            "customer_id": self.customer_id,
            "payment_id": self.payment_id,
            "amount_paise": self.amount_paise,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class PolicyDecisionLogger:
    """Centralized audit log for all policy decisions across the system.

    Every firewall, agent, and pipeline writes here.
    Provides query methods for demo and debugging.
    """

    def __init__(self) -> None:
        self._records: list[PolicyDecisionRecord] = []

    @property
    def records(self) -> list[PolicyDecisionRecord]:
        return list(self._records)

    def record(
        self,
        *,
        who: str,
        what: str,
        policy: str,
        reason: str,
        result: DecisionResult,
        customer_id: str | None = None,
        payment_id: str | None = None,
        amount_paise: int | None = None,
        context: dict | None = None,
    ) -> PolicyDecisionRecord:
        entry = PolicyDecisionRecord(
            who=who,
            what=what,
            policy=policy,
            reason=reason,
            result=result,
            customer_id=customer_id,
            payment_id=payment_id,
            amount_paise=amount_paise,
            context=context or {},
        )
        self._records.append(entry)
        return entry

    def get_by_customer(self, customer_id: str) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.customer_id == customer_id]

    def get_by_payment(self, payment_id: str) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.payment_id == payment_id]

    def get_blocked(self) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.result == DecisionResult.BLOCK]

    def get_human_review(self) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.result == DecisionResult.HUMAN_REVIEW]

    def get_allowed(self) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.result == DecisionResult.ALLOW]

    def get_by_actor(self, who: str) -> list[PolicyDecisionRecord]:
        return [r for r in self._records if r.who == who]

    def count_blocked(self) -> int:
        return len(self.get_blocked())

    def count_total(self) -> int:
        return len(self._records)
