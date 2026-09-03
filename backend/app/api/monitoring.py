from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.transaction_monitoring import (
    TransactionMonitoringRequest,
    TransactionMonitoringResponse,
)
from app.schemas.failure_analysis import (
    FailureAnalysisRequest,
    FailureAnalysisResponse,
)
from app.schemas.spike_detection import (
    SpikeDetectionRequest,
    SpikeDetectionResponse,
    DegradationMetric,
)
from app.services.monitoring.transaction_monitoring_service import (
    TransactionMonitoringService,
)
from app.services.monitoring.failure_analysis_service import (
    FailureAnalysisService,
)
from app.services.monitoring.spike_detection_service import (
    SpikeDetectionService,
)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/transactions", response_model=TransactionMonitoringResponse)
async def get_transaction_monitoring(
    time_window_hours: int = Query(24, ge=1, le=168),
    granularity: str = Query("hourly", regex="^(hourly|daily)$"),
    db: AsyncSession = Depends(get_db),
) -> TransactionMonitoringResponse:
    """Get transaction monitoring metrics and time series data."""
    svc = TransactionMonitoringService(db)

    metrics = await svc.get_metrics(time_window_hours)
    time_series = await svc.get_time_series(time_window_hours, granularity)

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=time_window_hours)

    return TransactionMonitoringResponse(
        metrics=metrics,
        time_series=time_series,
        period_start=period_start,
        period_end=now,
    )


@router.get("/transactions/summary")
async def get_transaction_summary(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a quick summary of transaction metrics."""
    svc = TransactionMonitoringService(db)
    metrics = await svc.get_metrics(time_window_hours)

    return {
        "success_rate": metrics.success_rate,
        "failure_rate": metrics.failure_rate,
        "revenue_at_risk": metrics.revenue_at_risk,
        "recovered_revenue": metrics.recovered_revenue,
        "total_transactions": metrics.total_transactions,
        "recovery_rate": metrics.recovery_rate,
    }


@router.get("/failures", response_model=FailureAnalysisResponse)
async def get_failure_analysis(
    time_window_hours: int = Query(24, ge=1, le=168),
    group_by: str = Query("failure_reason", regex="^(gateway|bank|region|payment_method|failure_reason)$"),
    db: AsyncSession = Depends(get_db),
) -> FailureAnalysisResponse:
    """Get failure analysis grouped by the specified dimension."""
    svc = FailureAnalysisService(db)
    return await svc.analyze(time_window_hours, group_by)


@router.get("/failures/summary")
async def get_failure_summary(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a summary of failure analysis across all dimensions."""
    svc = FailureAnalysisService(db)

    by_reason = await svc.analyze(time_window_hours, "failure_reason")
    by_gateway = await svc.analyze(time_window_hours, "gateway")
    by_bank = await svc.analyze(time_window_hours, "bank")
    by_region = await svc.analyze(time_window_hours, "region")
    by_method = await svc.analyze(time_window_hours, "payment_method")

    return {
        "total_failures": by_reason.total_failures,
        "revenue_at_risk": by_reason.revenue_at_risk,
        "by_failure_reason": [
            {"name": g.group_value, "count": g.failure_count, "revenue_at_risk": g.revenue_at_risk}
            for g in by_reason.groups[:5]
        ],
        "by_gateway": [
            {"name": g.group_value, "count": g.failure_count, "revenue_at_risk": g.revenue_at_risk}
            for g in by_gateway.groups[:5]
        ],
        "by_bank": [
            {"name": g.group_value, "count": g.failure_count, "revenue_at_risk": g.revenue_at_risk}
            for g in by_bank.groups[:5]
        ],
        "by_region": [
            {"name": g.group_value, "count": g.failure_count, "revenue_at_risk": g.revenue_at_risk}
            for g in by_region.groups[:5]
        ],
        "by_payment_method": [
            {"name": g.group_value, "count": g.failure_count, "revenue_at_risk": g.revenue_at_risk}
            for g in by_method.groups[:5]
        ],
    }


@router.get("/spikes", response_model=SpikeDetectionResponse)
async def detect_spikes(
    time_window_hours: int = Query(24, ge=1, le=168),
    threshold_multiplier: float = Query(2.0, ge=1.0, le=10.0),
    db: AsyncSession = Depends(get_db),
) -> SpikeDetectionResponse:
    """Detect spikes in payment failures."""
    svc = SpikeDetectionService(db)
    return await svc.detect_spikes(time_window_hours, threshold_multiplier)


@router.get("/degradation", response_model=list[DegradationMetric])
async def detect_degradation(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> list[DegradationMetric]:
    """Detect degradation in failure rates across dimensions."""
    svc = SpikeDetectionService(db)
    return await svc.detect_degradation(time_window_hours)
