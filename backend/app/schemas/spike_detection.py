from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SpikeDetectionRequest(BaseModel):
    time_window_hours: int = Field(default=24, ge=1, le=168, description="Time window in hours")
    threshold_multiplier: float = Field(default=2.0, ge=1.0, le=10.0, description="Threshold multiplier for spike detection")


class SpikeAlert(BaseModel):
    spike_type: str = Field(description="Type of spike detected")
    dimension: str = Field(description="Dimension where spike occurred (e.g., UPI, bank name)")
    current_count: int = Field(description="Current failure count")
    baseline_count: float = Field(description="Baseline failure count")
    threshold: float = Field(description="Threshold for spike detection")
    severity: str = Field(description="Severity level: low, medium, high, critical")
    revenue_impact: int = Field(description="Revenue impact in paise")
    detected_at: datetime
    message: str


class SpikeDetectionResponse(BaseModel):
    spikes_detected: bool
    spike_count: int
    spikes: list[SpikeAlert]
    period_start: datetime
    period_end: datetime
    baseline_period_start: datetime
    baseline_period_end: datetime


class DegradationMetric(BaseModel):
    dimension: str
    current_failure_rate: float
    previous_failure_rate: float
    change_percentage: float
    is_degraded: bool
    revenue_impact: int
