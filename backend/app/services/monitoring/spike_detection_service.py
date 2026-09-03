from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.payment import Payment, PaymentStatus
from app.schemas.spike_detection import SpikeAlert, SpikeDetectionResponse, DegradationMetric

logger = get_logger(__name__)


class SpikeDetectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_spikes(
        self,
        time_window_hours: int = 24,
        threshold_multiplier: float = 2.0,
    ) -> SpikeDetectionResponse:
        """Detect spikes in payment failures."""
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(hours=time_window_hours)
        baseline_start = current_start - timedelta(hours=time_window_hours)

        current_payments = await self._get_payments_in_window(current_start, now)
        baseline_payments = await self._get_payments_in_window(baseline_start, current_start)

        spikes = []

        upi_spike = self._check_dimension_spike(
            current_payments, baseline_payments, "payment_method", "UPI", threshold_multiplier
        )
        if upi_spike:
            spikes.append(upi_spike)

        bank_spikes = self._check_all_dimensions_spike(
            current_payments, baseline_payments, "bank", threshold_multiplier
        )
        spikes.extend(bank_spikes)

        gateway_spikes = self._check_all_dimensions_spike(
            current_payments, baseline_payments, "gateway", threshold_multiplier
        )
        spikes.extend(gateway_spikes)

        region_spikes = self._check_all_dimensions_spike(
            current_payments, baseline_payments, "region", threshold_multiplier
        )
        spikes.extend(region_spikes)

        reason_spikes = self._check_failure_reason_spikes(
            current_payments, baseline_payments, threshold_multiplier
        )
        spikes.extend(reason_spikes)

        return SpikeDetectionResponse(
            spikes_detected=len(spikes) > 0,
            spike_count=len(spikes),
            spikes=spikes,
            period_start=current_start,
            period_end=now,
            baseline_period_start=baseline_start,
            baseline_period_end=current_start,
        )

    async def detect_degradation(
        self,
        time_window_hours: int = 24,
    ) -> list[DegradationMetric]:
        """Detect degradation in failure rates across dimensions."""
        now = datetime.now(timezone.utc)
        current_start = now - timedelta(hours=time_window_hours)
        baseline_start = current_start - timedelta(hours=time_window_hours)

        current_payments = await self._get_payments_in_window(current_start, now)
        baseline_payments = await self._get_payments_in_window(baseline_start, current_start)

        degradation_metrics = []

        current_by_method = self._group_by_dimension(current_payments, "payment_method")
        baseline_by_method = self._group_by_dimension(baseline_payments, "payment_method")

        for method in set(list(current_by_method.keys()) + list(baseline_by_method.keys())):
            current_failures = len(current_by_method.get(method, []))
            baseline_failures = len(baseline_by_method.get(method, []))

            current_rate = current_failures / max(len(current_payments), 1) * 100
            baseline_rate = baseline_failures / max(len(baseline_payments), 1) * 100

            change = current_rate - baseline_rate
            is_degraded = change > 10

            revenue_impact = sum(p.amount for p in current_by_method.get(method, []))

            degradation_metrics.append(
                DegradationMetric(
                    dimension=f"payment_method:{method}",
                    current_failure_rate=round(current_rate, 2),
                    previous_failure_rate=round(baseline_rate, 2),
                    change_percentage=round(change, 2),
                    is_degraded=is_degraded,
                    revenue_impact=revenue_impact,
                )
            )

        current_by_bank = self._group_by_dimension(current_payments, "bank")
        baseline_by_bank = self._group_by_dimension(baseline_payments, "bank")

        for bank in set(list(current_by_bank.keys()) + list(baseline_by_bank.keys())):
            current_failures = len(current_by_bank.get(bank, []))
            baseline_failures = len(baseline_by_bank.get(bank, []))

            current_rate = current_failures / max(len(current_payments), 1) * 100
            baseline_rate = baseline_failures / max(len(baseline_payments), 1) * 100

            change = current_rate - baseline_rate
            is_degraded = change > 10

            revenue_impact = sum(p.amount for p in current_by_bank.get(bank, []))

            degradation_metrics.append(
                DegradationMetric(
                    dimension=f"bank:{bank}",
                    current_failure_rate=round(current_rate, 2),
                    previous_failure_rate=round(baseline_rate, 2),
                    change_percentage=round(change, 2),
                    is_degraded=is_degraded,
                    revenue_impact=revenue_impact,
                )
            )

        return degradation_metrics

    async def _get_payments_in_window(
        self, start: datetime, end: datetime
    ) -> Sequence[Payment]:
        """Get all failed payments in a time window."""
        query = select(Payment).where(
            and_(
                Payment.created_at >= start,
                Payment.created_at < end,
                Payment.status.in_([
                    PaymentStatus.FAILED.value,
                    PaymentStatus.RECOVERY_PENDING.value,
                ]),
            )
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    def _group_by_dimension(
        self, payments: Sequence[Payment], dimension: str
    ) -> dict[str, list[Payment]]:
        """Group payments by a specific dimension."""
        grouped: dict[str, list[Payment]] = {}

        for payment in payments:
            key = self._extract_dimension(payment, dimension)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(payment)

        return grouped

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
        else:
            return "unknown"

    def _check_dimension_spike(
        self,
        current_payments: Sequence[Payment],
        baseline_payments: Sequence[Payment],
        dimension: str,
        dimension_value: str,
        threshold_multiplier: float,
    ) -> SpikeAlert | None:
        """Check if there's a spike in a specific dimension."""
        current_count = sum(
            1 for p in current_payments
            if self._extract_dimension(p, dimension) == dimension_value
        )
        baseline_count = sum(
            1 for p in baseline_payments
            if self._extract_dimension(p, dimension) == dimension_value
        )

        threshold = baseline_count * threshold_multiplier

        if current_count > threshold and current_count >= 3:
            revenue_impact = sum(
                p.amount for p in current_payments
                if self._extract_dimension(p, dimension) == dimension_value
            )

            severity = self._calculate_severity(current_count, baseline_count, threshold_multiplier)

            return SpikeAlert(
                spike_type=f"{dimension}_spike",
                dimension=f"{dimension}:{dimension_value}",
                current_count=current_count,
                baseline_count=baseline_count,
                threshold=threshold,
                severity=severity,
                revenue_impact=revenue_impact,
                detected_at=datetime.now(timezone.utc),
                message=f"Spike detected in {dimension_value} {dimension}: {current_count} failures vs {baseline_count} baseline",
            )

        return None

    def _check_all_dimensions_spike(
        self,
        current_payments: Sequence[Payment],
        baseline_payments: Sequence[Payment],
        dimension: str,
        threshold_multiplier: float,
    ) -> list[SpikeAlert]:
        """Check for spikes across all values of a dimension."""
        current_groups = self._group_by_dimension(current_payments, dimension)
        baseline_groups = self._group_by_dimension(baseline_payments, dimension)

        spikes = []

        for value in set(list(current_groups.keys()) + list(baseline_groups.keys())):
            if value == "unknown":
                continue

            spike = self._check_dimension_spike(
                current_groups.get(value, []),
                baseline_groups.get(value, []),
                dimension,
                value,
                threshold_multiplier,
            )
            if spike:
                spikes.append(spike)

        return spikes

    def _check_failure_reason_spikes(
        self,
        current_payments: Sequence[Payment],
        baseline_payments: Sequence[Payment],
        threshold_multiplier: float,
    ) -> list[SpikeAlert]:
        """Check for spikes in specific failure reasons."""
        current_reasons: dict[str, int] = {}
        baseline_reasons: dict[str, int] = {}

        for p in current_payments:
            reason = p.failure_reason or "unknown"
            current_reasons[reason] = current_reasons.get(reason, 0) + 1

        for p in baseline_payments:
            reason = p.failure_reason or "unknown"
            baseline_reasons[reason] = baseline_reasons.get(reason, 0) + 1

        spikes = []

        for reason, current_count in current_reasons.items():
            baseline_count = baseline_reasons.get(reason, 0)
            threshold = baseline_count * threshold_multiplier

            if current_count > threshold and current_count >= 3:
                revenue_impact = sum(
                    p.amount for p in current_payments
                    if (p.failure_reason or "unknown") == reason
                )

                severity = self._calculate_severity(current_count, baseline_count, threshold_multiplier)

                spikes.append(
                    SpikeAlert(
                        spike_type="failure_reason_spike",
                        dimension=f"failure_reason:{reason}",
                        current_count=current_count,
                        baseline_count=baseline_count,
                        threshold=threshold,
                        severity=severity,
                        revenue_impact=revenue_impact,
                        detected_at=datetime.now(timezone.utc),
                        message=f"Spike in failure reason '{reason}': {current_count} vs {baseline_count} baseline",
                    )
                )

        return spikes

    def _calculate_severity(
        self, current: int, baseline: int, multiplier: float
    ) -> str:
        """Calculate severity based on spike magnitude."""
        if baseline == 0:
            ratio = current
        else:
            ratio = current / baseline

        if ratio >= multiplier * 2 or current >= 20:
            return "critical"
        elif ratio >= multiplier * 1.5 or current >= 10:
            return "high"
        elif ratio >= multiplier:
            return "medium"
        else:
            return "low"
