from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class InvestigationCreate(BaseModel):
    incident_id: uuid.UUID
    payment_id: uuid.UUID | None = None
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    metadata_: dict | None = None


class InvestigationUpdate(BaseModel):
    state: Literal["observe", "query", "correlate", "diagnose", "completed", "failed"] | None = None
    status: Literal["pending", "in_progress", "completed", "failed"] | None = None
    description: str | None = None
    query_results: dict | None = None
    correlation_results: dict | None = None
    diagnosis: dict | None = None
    metadata_: dict | None = None


class InvestigationResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    payment_id: uuid.UUID | None
    state: str
    status: str
    title: str
    description: str | None
    query_results: dict | None
    correlation_results: dict | None
    diagnosis: dict | None
    started_at: datetime | None
    completed_at: datetime | None
    metadata_: dict | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvestigationListResponse(BaseModel):
    items: list[InvestigationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class InvestigationStateTransition(BaseModel):
    from_state: str
    to_state: str
    timestamp: datetime
    details: dict | None = None


class QueryResult(BaseModel):
    dimension: str
    value: str
    count: int
    revenue_impact: int
    percentage: float


class CorrelationResult(BaseModel):
    dimension: str
    value: str
    contribution_score: float
    confidence: float
    rank: int


class DiagnosisOutput(BaseModel):
    primary_contributor: str
    contributor_dimension: str
    affected_region: str | None
    failure_pattern: str
    confidence: float
    summary: str
    recommendation: str
