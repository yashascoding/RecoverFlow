from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.schemas.investigation import (
    QueryResult,
    CorrelationResult,
    DiagnosisOutput,
)
from app.services.investigation.investigation_query_service import InvestigationQueryService
from app.services.investigation.correlation_analysis_service import CorrelationAnalysisService

logger = get_logger(__name__)


class AIDiagnosisService:
    """Service for generating AI-powered diagnosis from investigation data."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.query_service = InvestigationQueryService(db)
        self.correlation_service = CorrelationAnalysisService(db)

    async def generate_diagnosis(
        self,
        time_window_hours: int = 24,
        incident_context: dict | None = None,
    ) -> DiagnosisOutput:
        """Generate a comprehensive diagnosis from investigation data."""
        failure_pattern = await self.query_service.query_failure_pattern(time_window_hours)
        top_contributors = await self.correlation_service.get_top_contributors(
            time_window_hours, limit=5
        )

        primary_contributor = top_contributors[0] if top_contributors else None

        affected_region = self._identify_affected_region(failure_pattern)
        failure_pattern_desc = self._describe_failure_pattern(failure_pattern)
        confidence = self._calculate_diagnosis_confidence(
            primary_contributor, failure_pattern
        )

        summary = self._generate_summary(
            primary_contributor, affected_region, failure_pattern, confidence
        )

        recommendation = self._generate_recommendation(
            primary_contributor, failure_pattern
        )

        return DiagnosisOutput(
            primary_contributor=primary_contributor.value if primary_contributor else "unknown",
            contributor_dimension=primary_contributor.dimension if primary_contributor else "unknown",
            affected_region=affected_region,
            failure_pattern=failure_pattern_desc,
            confidence=confidence,
            summary=summary,
            recommendation=recommendation,
        )

    async def diagnose_from_correlation(
        self,
        correlation_results: list[CorrelationResult],
        failure_pattern: dict,
    ) -> DiagnosisOutput:
        """Generate diagnosis from pre-computed correlation results."""
        primary_contributor = correlation_results[0] if correlation_results else None

        affected_region = self._identify_affected_region(failure_pattern)
        failure_pattern_desc = self._describe_failure_pattern(failure_pattern)
        confidence = self._calculate_diagnosis_confidence(
            primary_contributor, failure_pattern
        )

        summary = self._generate_summary(
            primary_contributor, affected_region, failure_pattern, confidence
        )

        recommendation = self._generate_recommendation(
            primary_contributor, failure_pattern
        )

        return DiagnosisOutput(
            primary_contributor=primary_contributor.value if primary_contributor else "unknown",
            contributor_dimension=primary_contributor.dimension if primary_contributor else "unknown",
            affected_region=affected_region,
            failure_pattern=failure_pattern_desc,
            confidence=confidence,
            summary=summary,
            recommendation=recommendation,
        )

    def _identify_affected_region(self, failure_pattern: dict) -> str | None:
        """Identify the most affected region from failure pattern."""
        region_distribution = failure_pattern.get("bank_distribution", {})
        if region_distribution:
            top_region = max(region_distribution.items(), key=lambda x: x[1])
            return top_region[0]
        return None

    def _describe_failure_pattern(self, failure_pattern: dict) -> str:
        """Describe the failure pattern in human-readable format."""
        total_failures = failure_pattern.get("total_failures", 0)
        top_method = failure_pattern.get("top_payment_method", "unknown")
        top_bank = failure_pattern.get("top_bank", "unknown")
        top_reason = failure_pattern.get("top_failure_reason", "unknown")

        return (
            f"{total_failures} failures detected. "
            f"Primary payment method: {top_method}. "
            f"Most affected bank: {top_bank}. "
            f"Top failure reason: {top_reason}."
        )

    def _calculate_diagnosis_confidence(
        self,
        primary_contributor: CorrelationResult | None,
        failure_pattern: dict,
    ) -> float:
        """Calculate confidence score for the diagnosis."""
        if not primary_contributor:
            return 0.3

        base_confidence = primary_contributor.confidence

        total_failures = failure_pattern.get("total_failures", 0)
        if total_failures > 100:
            base_confidence += 0.1
        elif total_failures > 50:
            base_confidence += 0.05

        if primary_contributor.contribution_score > 0.5:
            base_confidence += 0.1

        return min(round(base_confidence, 2), 0.99)

    def _generate_summary(
        self,
        primary_contributor: CorrelationResult | None,
        affected_region: str | None,
        failure_pattern: dict,
        confidence: float,
    ) -> str:
        """Generate a human-readable summary."""
        if not primary_contributor:
            return "Insufficient data to generate diagnosis."

        total_revenue = failure_pattern.get("total_revenue_at_risk", 0)
        revenue_str = f"₹{total_revenue // 100}" if total_revenue > 0 else "unknown"

        region_str = f"Affected region: {affected_region}" if affected_region else ""

        return (
            f"Payment failure analysis reveals {primary_contributor.dimension} "
            f"'{primary_contributor.value}' as the primary contributor with "
            f"{primary_contributor.contribution_score:.1%} contribution score. "
            f"Revenue at risk: {revenue_str}. {region_str}. "
            f"Diagnosis confidence: {confidence:.0%}."
        )

    def _generate_recommendation(
        self,
        primary_contributor: CorrelationResult | None,
        failure_pattern: dict,
    ) -> str:
        """Generate actionable recommendation."""
        if not primary_contributor:
            return "Collect more data before taking action."

        dimension = primary_contributor.dimension
        value = primary_contributor.value

        if dimension == "payment_method":
            if value.lower() == "upi":
                return (
                    "UPI failures detected. Recommend: "
                    "1) Check UPI gateway health, "
                    "2) Enable retry mechanism, "
                    "3) Offer alternative payment methods."
                )
            return f"Investigate {value} payment method issues."

        elif dimension == "bank":
            return (
                f"Bank '{value}' showing high failure rate. Recommend: "
                "1) Contact bank for status, "
                "2) Implement bank-specific retry logic, "
                "3) Consider routing optimization."
            )

        elif dimension == "gateway":
            return (
                f"Gateway '{value}' experiencing issues. Recommend: "
                "1) Check gateway status page, "
                "2) Implement failover to secondary gateway, "
                "3) Monitor latency metrics."
            )

        elif dimension == "region":
            return (
                f"Region '{value}' affected. Recommend: "
                "1) Check local network conditions, "
                "2) Verify regional bank integrations, "
                "3) Consider regional payment preferences."
            )

        elif dimension == "failure_reason":
            return (
                f"Failure reason '{value}' dominant. Recommend: "
                "1) Implement specific handling for this error, "
                "2) Update user messaging, "
                "3) Add retry logic where appropriate."
            )

        return f"Investigate {dimension} = {value} further."
