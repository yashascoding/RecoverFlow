from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.schemas.transaction_monitoring import (
    TransactionMetrics,
    TimeSeriesPoint,
)

logger = get_logger(__name__)


class TransactionMonitoringService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_metrics(
        self, time_window_hours: int = 24
    ) -> TransactionMetrics:
        """Calculate transaction monitoring metrics for the given time window."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=time_window_hours)

        query = select(Payment).where(
            Payment.created_at >= start_time
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        return self._calculate_metrics(payments)

    async def get_time_series(
        self,
        time_window_hours: int = 24,
        granularity: str = "hourly",
    ) -> list[TimeSeriesPoint]:
        """Get time series data for transaction monitoring."""
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=time_window_hours)

        if granularity == "hourly":
            interval = timedelta(hours=1)
        else:
            interval = timedelta(days=1)

        time_series = []
        current_time = start_time

        while current_time < now:
            next_time = current_time + interval

            query = select(Payment).where(
                and_(
                    Payment.created_at >= current_time,
                    Payment.created_at < next_time,
                )
            )
            result = await self.db.execute(query)
            payments = list(result.scalars().all())

            metrics = self._calculate_metrics(payments)

            time_series.append(
                TimeSeriesPoint(
                    timestamp=current_time,
                    success_rate=metrics.success_rate,
                    failure_rate=metrics.failure_rate,
                    revenue_at_risk=metrics.revenue_at_risk,
                    recovered_revenue=metrics.recovered_revenue,
                    total_transactions=metrics.total_transactions,
                )
            )

            current_time = next_time

        return time_series

    def _calculate_metrics(self, payments: Sequence[Payment]) -> TransactionMetrics:
        """Calculate metrics from a list of payments."""
        total = len(payments)

        if total == 0:
            return TransactionMetrics(
                total_transactions=0,
                successful_transactions=0,
                failed_transactions=0,
                success_rate=0.0,
                failure_rate=0.0,
                revenue_at_risk=0,
                recovered_revenue=0,
                total_revenue=0,
                recovery_rate=0.0,
            )

        successful = [
            p for p in payments
            if p.status in (PaymentStatus.CAPTURED.value, PaymentStatus.RECOVERED.value)
        ]
        failed = [
            p for p in payments
            if p.status in (PaymentStatus.FAILED.value, PaymentStatus.RECOVERY_PENDING.value)
        ]
        recovered = [
            p for p in payments
            if p.status == PaymentStatus.RECOVERED.value
        ]

        total_revenue = sum(p.amount for p in successful)
        revenue_at_risk = sum(p.amount for p in failed)
        recovered_revenue = sum(p.amount for p in recovered)

        success_rate = round((len(successful) / total) * 100, 2) if total > 0 else 0.0
        failure_rate = round((len(failed) / total) * 100, 2) if total > 0 else 0.0
        recovery_rate = round((len(recovered) / len(failed) * 100), 2) if failed else 0.0

        return TransactionMetrics(
            total_transactions=total,
            successful_transactions=len(successful),
            failed_transactions=len(failed),
            success_rate=success_rate,
            failure_rate=failure_rate,
            revenue_at_risk=revenue_at_risk,
            recovered_revenue=recovered_revenue,
            total_revenue=total_revenue,
            recovery_rate=recovery_rate,
        )
