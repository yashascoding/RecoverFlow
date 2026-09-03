from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    alert_type: str = Field(..., min_length=1, max_length=100)
    metric_name: str = Field(..., min_length=1, max_length=100)
    threshold_value: float
    comparison_operator: Literal["gt", "gte", "lt", "lte", "eq"]
    time_window_minutes: int = Field(default=60, ge=1)
    cooldown_minutes: int = Field(default=30, ge=0)
    metadata_: dict | None = None


class AlertUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: Literal["active", "triggered", "resolved", "disabled"] | None = None
    severity: Literal["low", "medium", "high", "critical"] | None = None
    threshold_value: float | None = None
    comparison_operator: Literal["gt", "gte", "lt", "lte", "eq"] | None = None
    time_window_minutes: int | None = None
    cooldown_minutes: int | None = None
    metadata_: dict | None = None


class AlertResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: str
    severity: str
    alert_type: str
    metric_name: str
    threshold_value: float
    comparison_operator: str
    time_window_minutes: int
    cooldown_minutes: int
    last_triggered_at: datetime | None
    last_value: float | None
    incident_id: uuid.UUID | None
    metadata_: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    items: list[AlertResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AlertTestRequest(BaseModel):
    metric_value: float
    alert_id: uuid.UUID | None = None


class AlertTestResponse(BaseModel):
    would_trigger: bool
    current_value: float
    threshold_value: float
    comparison_operator: str
    alert_name: str
    message: str
