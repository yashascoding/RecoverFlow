from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.schemas.investigation import DiagnosisOutput, CorrelationResult

logger = get_logger(__name__)


class RecoveryStrategy:
    """Recovery strategy output."""
    
    def __init__(
        self,
        *,
        strategy_name: str,
        description: str,
        actions: list[dict],
        estimated_recovery_rate: float,
        priority: str,
        timeline: str,
        resources_required: list[str],
    ) -> None:
        self.strategy_name = strategy_name
        self.description = description
        self.actions = actions
        self.estimated_recovery_rate = estimated_recovery_rate
        self.priority = priority
        self.timeline = timeline
        self.resources_required = resources_required

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "description": self.description,
            "actions": self.actions,
            "estimated_recovery_rate": self.estimated_recovery_rate,
            "priority": self.priority,
            "timeline": self.timeline,
            "resources_required": self.resources_required,
        }


class RecoveryStrategyService:
    """Service for generating recovery strategies from diagnosis."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def generate_strategy(
        self,
        diagnosis: DiagnosisOutput,
        correlation_results: list[CorrelationResult] | None = None,
    ) -> RecoveryStrategy:
        """Generate a recovery strategy based on diagnosis."""
        dimension = diagnosis.contributor_dimension
        contributor = diagnosis.primary_contributor
        confidence = diagnosis.confidence

        if dimension == "payment_method":
            return self._payment_method_strategy(contributor, confidence)
        elif dimension == "bank":
            return self._bank_strategy(contributor, confidence)
        elif dimension == "gateway":
            return self._gateway_strategy(contributor, confidence)
        elif dimension == "region":
            return self._region_strategy(contributor, confidence)
        elif dimension == "failure_reason":
            return self._failure_reason_strategy(contributor, confidence)
        else:
            return self._generic_strategy(diagnosis)

    def _payment_method_strategy(
        self, contributor: str, confidence: float
    ) -> RecoveryStrategy:
        """Generate strategy for payment method issues."""
        if contributor.lower() == "upi":
            return RecoveryStrategy(
                strategy_name="UPI Recovery Enhancement",
                description=(
                    "Address UPI payment failures through retry optimization "
                    "and alternative payment method promotion."
                ),
                actions=[
                    {
                        "action": "Enable automatic retry",
                        "description": "Implement 3-retry mechanism with exponential backoff",
                        "priority": "high",
                    },
                    {
                        "action": "Promote alternative methods",
                        "description": "Show cards and net banking options prominently",
                        "priority": "medium",
                    },
                    {
                        "action": "Implement UPI timeout handling",
                        "description": "Add 30-second timeout with graceful fallback",
                        "priority": "high",
                    },
                    {
                        "action": "Send recovery emails",
                        "description": "Trigger recovery email campaign for failed UPI transactions",
                        "priority": "medium",
                    },
                ],
                estimated_recovery_rate=0.75,
                priority="high",
                timeline="1-2 hours",
                resources_required=["Payment Gateway Team", "Backend Developer"],
            )
        else:
            return RecoveryStrategy(
                strategy_name=f"{contributor} Payment Method Recovery",
                description=f"Address {contributor} payment method failures.",
                actions=[
                    {
                        "action": "Investigate method-specific issues",
                        "description": f"Check {contributor} integration health",
                        "priority": "high",
                    },
                ],
                estimated_recovery_rate=0.60,
                priority="medium",
                timeline="2-4 hours",
                resources_required=["Payment Team"],
            )

    def _bank_strategy(
        self, contributor: str, confidence: float
    ) -> RecoveryStrategy:
        """Generate strategy for bank-related issues."""
        return RecoveryStrategy(
            strategy_name=f"Bank {contributor} Recovery",
            description=(
                f"Address high failure rate from {contributor} through "
                "retry optimization and bank communication."
            ),
            actions=[
                {
                    "action": "Check bank status",
                    "description": f"Verify {contributor} API health and status page",
                    "priority": "high",
                },
                {
                    "action": "Implement bank-specific retry",
                    "description": f"Add retry logic optimized for {contributor} patterns",
                    "priority": "high",
                },
                {
                    "action": "Contact bank support",
                    "description": f"Reach out to {contributor} technical team",
                    "priority": "medium",
                },
                {
                    "action": "Route optimization",
                    "description": "Consider routing through alternate bank if available",
                    "priority": "low",
                },
            ],
            estimated_recovery_rate=0.65,
            priority="high",
            timeline="2-6 hours",
            resources_required=["Payment Gateway Team", "Business Development"],
        )

    def _gateway_strategy(
        self, contributor: str, confidence: float
    ) -> RecoveryStrategy:
        """Generate strategy for gateway issues."""
        return RecoveryStrategy(
            strategy_name=f"Gateway {contributor} Recovery",
            description=(
                f"Address gateway {contributor} issues through failover "
                "and monitoring."
            ),
            actions=[
                {
                    "action": "Check gateway status",
                    "description": f"Verify {contributor} service health",
                    "priority": "critical",
                },
                {
                    "action": "Enable failover",
                    "description": "Switch to secondary gateway if available",
                    "priority": "high",
                },
                {
                    "action": "Monitor latency",
                    "description": "Track response times and error rates",
                    "priority": "high",
                },
                {
                    "action": "Notify operations",
                    "description": "Alert ops team about gateway degradation",
                    "priority": "medium",
                },
            ],
            estimated_recovery_rate=0.70,
            priority="critical",
            timeline="30 minutes - 2 hours",
            resources_required=["DevOps", "Payment Gateway Team"],
        )

    def _region_strategy(
        self, contributor: str, confidence: float
    ) -> RecoveryStrategy:
        """Generate strategy for regional issues."""
        return RecoveryStrategy(
            strategy_name=f"Region {contributor} Recovery",
            description=(
                f"Address regional payment issues in {contributor} "
                "through localized strategies."
            ),
            actions=[
                {
                    "action": "Check regional bank status",
                    "description": "Verify banks operating in the region",
                    "priority": "high",
                },
                {
                    "action": "Analyze regional patterns",
                    "description": "Identify time-of-day or day-of-week patterns",
                    "priority": "medium",
                },
                {
                    "action": "Regional payment preferences",
                    "description": "Promote locally preferred payment methods",
                    "priority": "medium",
                },
            ],
            estimated_recovery_rate=0.55,
            priority="medium",
            timeline="4-8 hours",
            resources_required=["Data Analyst", "Payment Team"],
        )

    def _failure_reason_strategy(
        self, contributor: str, confidence: float
    ) -> RecoveryStrategy:
        """Generate strategy for specific failure reasons."""
        strategies = {
            "insufficient_funds": RecoveryStrategy(
                strategy_name="Insufficient Funds Recovery",
                description="Address insufficient funds failures through retry timing.",
                actions=[
                    {
                        "action": "Retry after delay",
                        "description": "Retry payment after 24-48 hours",
                        "priority": "high",
                    },
                    {
                        "action": "Send reminder email",
                        "description": "Notify customer about failed payment",
                        "priority": "medium",
                    },
                ],
                estimated_recovery_rate=0.40,
                priority="medium",
                timeline="24-48 hours",
                resources_required=["Email Service"],
            ),
            "expired_card": RecoveryStrategy(
                strategy_name="Expired Card Recovery",
                description="Handle expired card failures through card update prompts.",
                actions=[
                    {
                        "action": "Prompt card update",
                        "description": "Ask customer to update card details",
                        "priority": "high",
                    },
                ],
                estimated_recovery_rate=0.30,
                priority="low",
                timeline="1-3 days",
                resources_required=["Frontend Team"],
            ),
        }

        return strategies.get(
            contributor.lower(),
            RecoveryStrategy(
                strategy_name=f"Recovery for {contributor}",
                description=f"Address {contributor} failures.",
                actions=[
                    {
                        "action": "Investigate root cause",
                        "description": f"Deep dive into {contributor} failures",
                        "priority": "high",
                    },
                ],
                estimated_recovery_rate=0.50,
                priority="medium",
                timeline="2-4 hours",
                resources_required=["Engineering Team"],
            ),
        )

    def _generic_strategy(self, diagnosis: DiagnosisOutput) -> RecoveryStrategy:
        """Generate generic recovery strategy."""
        return RecoveryStrategy(
            strategy_name="Generic Recovery Strategy",
            description="Standard recovery approach for identified issues.",
            actions=[
                {
                    "action": "Analyze failure patterns",
                    "description": "Deep dive into failure data",
                    "priority": "high",
                },
                {
                    "action": "Implement retry logic",
                    "description": "Add intelligent retry mechanism",
                    "priority": "high",
                },
                {
                    "action": "Send recovery communications",
                    "description": "Notify affected customers",
                    "priority": "medium",
                },
            ],
            estimated_recovery_rate=0.50,
            priority="medium",
            timeline="2-6 hours",
            resources_required=["Engineering Team"],
        )
