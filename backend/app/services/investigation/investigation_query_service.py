from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.schemas.investigation import QueryResult

logger = get_logger(__name__)


class InvestigationQueryService:
    """Service for querying payment data across different dimensions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def query_by_dimension(
        self,
        dimension: str,
        time_window_hours: int = 24,
        incident_id: str | None = None,
    ) -> list[QueryResult]:
        """Query failures grouped by a specific dimension."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=time_window_hours)

        query = select(Payment).where(
            and_(
                Payment.created_at >= start_time,
                Payment.status.in_([
                    PaymentStatus.FAILED.value,
                    PaymentStatus.RECOVERY_PENDING.value,
                ]),
            )
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        return self._group_by_dimension(payments, dimension)

    async def query_all_dimensions(
        self,
        time_window_hours: int = 24,
    ) -> dict[str, list[QueryResult]]:
        """Query failures across all dimensions."""
        dimensions = ["gateway", "bank", "region", "payment_method", "failure_reason"]
        results = {}

        for dimension in dimensions:
            results[dimension] = await self.query_by_dimension(dimension, time_window_hours)

        return results

    async def query_top_contributors(
        self,
        dimension: str,
        time_window_hours: int = 24,
        limit: int = 10,
    ) -> list[QueryResult]:
        """Query top contributors for a specific dimension."""
        results = await self.query_by_dimension(dimension, time_window_hours)
        return sorted(results, key=lambda x: x.revenue_impact, reverse=True)[:limit]

    async def query_failure_pattern(
        self,
        time_window_hours: int = 24,
    ) -> dict:
        """Query overall failure pattern."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=time_window_hours)

        query = select(Payment).where(
            and_(
                Payment.created_at >= start_time,
                Payment.status.in_([
                    PaymentStatus.FAILED.value,
                    PaymentStatus.RECOVERY_PENDING.value,
                ]),
            )
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        total_failures = len(payments)
        total_revenue_at_risk = sum(p.amount for p in payments)

        by_method = self._group_by_dimension(payments, "payment_method")
        by_bank = self._group_by_dimension(payments, "bank")
        by_reason = self._group_by_dimension(payments, "failure_reason")

        return {
            "total_failures": total_failures,
            "total_revenue_at_risk": total_revenue_at_risk,
            "top_payment_method": by_method[0].value if by_method else "unknown",
            "top_bank": by_bank[0].value if by_bank else "unknown",
            "top_failure_reason": by_reason[0].value if by_reason else "unknown",
            "payment_method_distribution": {r.value: r.percentage for r in by_method[:5]},
            "bank_distribution": {r.value: r.percentage for r in by_bank[:5]},
            "failure_reason_distribution": {r.value: r.percentage for r in by_reason[:5]},
        }

    def _group_by_dimension(
        self, payments: Sequence[Payment], dimension: str
    ) -> list[QueryResult]:
        """Group payments by a specific dimension."""
        grouped: dict[str, list[Payment]] = {}

        for payment in payments:
            key = self._extract_dimension(payment, dimension)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(payment)

        total = len(payments)
        results = []

        for key, group_payments in grouped.items():
            revenue_impact = sum(p.amount for p in group_payments)
            percentage = round(
                (len(group_payments) / total * 100) if total > 0 else 0,
                2
            )

            results.append(
                QueryResult(
                    dimension=dimension,
                    value=key,
                    count=len(group_payments),
                    revenue_impact=revenue_impact,
                    percentage=percentage,
                )
            )

        return sorted(results, key=lambda x: x.revenue_impact, reverse=True)

    def _extract_dimension(self, payment: Payment, dimension: str) -> str:
        """Extract a dimension value from a payment."""
        metadata = payment.metadata_ or {}

        if dimension == "payment_method":
            return metadata.get("method", metadata.get("payment_method", "unknown"))
        elif dimension == "bank":
            return metadata.get("bank", metadata.get("issuing_bank", "unknown"))
        elif dimension == "gateway":
            return metadata.get("gateway", metadata.get("payment_gateway", "unknown"))
        elif dimension == "region":
            return metadata.get("region", metadata.get("city", "unknown"))
        elif dimension == "failure_reason":
            return payment.failure_reason or "unknown"
        else:
            return "unknown"
