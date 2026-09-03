from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.schemas.failure_analysis import FailureGroup, FailureAnalysisResponse

logger = get_logger(__name__)


class FailureAnalysisService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def analyze(
        self,
        time_window_hours: int = 24,
        group_by: str = "failure_reason",
    ) -> FailureAnalysisResponse:
        """Analyze failures grouped by the specified dimension."""
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

        groups = self._group_payments(payments, group_by, total_failures)

        return FailureAnalysisResponse(
            total_failures=total_failures,
            revenue_at_risk=total_revenue_at_risk,
            groups=groups,
            period_start=start_time,
            period_end=now,
            group_by=group_by,
        )

    def _group_payments(
        self,
        payments: Sequence[Payment],
        group_by: str,
        total_failures: int,
    ) -> list[FailureGroup]:
        """Group payments by the specified dimension."""
        grouped: dict[str, list[Payment]] = {}

        for payment in payments:
            key = self._extract_group_key(payment, group_by)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(payment)

        groups = []
        for key, group_payments in grouped.items():
            revenue_at_risk = sum(p.amount for p in group_payments)
            percentage = round(
                (len(group_payments) / total_failures * 100) if total_failures > 0 else 0,
                2
            )

            top_reasons = self._get_top_failure_reasons(group_payments)

            groups.append(
                FailureGroup(
                    group_name=group_by,
                    group_value=key,
                    failure_count=len(group_payments),
                    revenue_at_risk=revenue_at_risk,
                    percentage=percentage,
                    top_failure_reasons=top_reasons,
                )
            )

        groups.sort(key=lambda x: x.failure_count, reverse=True)
        return groups

    def _extract_group_key(self, payment: Payment, group_by: str) -> str:
        """Extract the grouping key from a payment based on the dimension."""
        metadata = payment.metadata_ or {}

        if group_by == "gateway":
            return metadata.get("gateway", metadata.get("payment_gateway", "unknown"))
        elif group_by == "bank":
            return metadata.get("bank", metadata.get("issuing_bank", "unknown"))
        elif group_by == "region":
            return metadata.get("region", metadata.get("city", "unknown"))
        elif group_by == "payment_method":
            return metadata.get("method", metadata.get("payment_method", "unknown"))
        elif group_by == "failure_reason":
            return payment.failure_reason or "unknown"
        else:
            return "unknown"

    def _get_top_failure_reasons(self, payments: Sequence[Payment]) -> list[str]:
        """Get the top failure reasons for a group of payments."""
        reason_counts: dict[str, int] = {}
        for payment in payments:
            reason = payment.failure_reason or "unknown"
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        sorted_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
        return [reason for reason, _ in sorted_reasons[:3]]
