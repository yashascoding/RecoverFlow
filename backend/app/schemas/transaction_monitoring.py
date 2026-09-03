from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TransactionMonitoringRequest(BaseModel):
    time_window_hours: int = Field(default=24, ge=1, le=168, description="Time window in hours")
    granularity: Literal["hourly", "daily"] = Field(default="hourly", description="Data granularity")


class TransactionMetrics(BaseModel):
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    success_rate: float = Field(description="Success rate as percentage (0-100)")
    failure_rate: float = Field(description="Failure rate as percentage (0-100)")
    revenue_at_risk: int = Field(description="Revenue at risk in paise")
    recovered_revenue: int = Field(description="Recovered revenue in paise")
    total_revenue: int = Field(description="Total captured revenue in paise")
    recovery_rate: float = Field(description="Recovery rate as percentage (0-100)")


class TimeSeriesPoint(BaseModel):
    timestamp: datetime
    success_rate: float
    failure_rate: float
    revenue_at_risk: int
    recovered_revenue: int
    total_transactions: int


class TransactionMonitoringResponse(BaseModel):
    metrics: TransactionMetrics
    time_series: list[TimeSeriesPoint]
    period_start: datetime
    period_end: datetime
