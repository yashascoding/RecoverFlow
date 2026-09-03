from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    incident_type: str = Field(..., min_length=1, max_length=100)
    affected_gateway: str | None = None
    affected_bank: str | None = None
    affected_region: str | None = None
    affected_payment_method: str | None = None
    failure_reason: str | None = None
    revenue_at_risk: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    baseline_failure_count: float = Field(default=0.0, ge=0)
    spike_threshold: float = Field(default=0.0, ge=0)
    detected_at: datetime
    metadata_: dict | None = None


class IncidentUpdate(BaseModel):
    status: Literal["open", "investigating", "resolved", "escalated"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    description: str | None = None
    resolved_at: datetime | None = None
    metadata_: dict | None = None


class IncidentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    severity: str
    incident_type: str
    affected_gateway: str | None
    affected_bank: str | None
    affected_region: str | None
    affected_payment_method: str | None
    failure_reason: str | None
    revenue_at_risk: int
    failure_count: int
    baseline_failure_count: float
    spike_threshold: float
    detected_at: datetime
    resolved_at: datetime | None
    metadata_: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class IncidentStatsResponse(BaseModel):
    total_incidents: int
    open_incidents: int
    investigating_incidents: int
    resolved_incidents: int
    escalated_incidents: int
    total_revenue_at_risk: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
