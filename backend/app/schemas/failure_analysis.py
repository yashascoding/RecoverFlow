from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class FailureAnalysisRequest(BaseModel):
    time_window_hours: int = Field(default=24, ge=1, le=168, description="Time window in hours")
    group_by: Literal["gateway", "bank", "region", "payment_method", "failure_reason"] = Field(
        default="failure_reason",
        description="Dimension to group failures by"
    )


class FailureGroup(BaseModel):
    group_name: str
    group_value: str
    failure_count: int
    revenue_at_risk: int = Field(description="Revenue at risk in paise")
    percentage: float = Field(description="Percentage of total failures")
    top_failure_reasons: list[str] = Field(default_factory=list)


class FailureAnalysisResponse(BaseModel):
    total_failures: int
    revenue_at_risk: int
    groups: list[FailureGroup]
    period_start: datetime
    period_end: datetime
    group_by: str
