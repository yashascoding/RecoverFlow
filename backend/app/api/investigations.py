from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationUpdate,
    InvestigationResponse,
    InvestigationListResponse,
    QueryResult,
    CorrelationResult,
    DiagnosisOutput,
)
from app.services.investigation.investigation_service import (
    InvestigationService,
    InvalidStateTransitionError,
)
from app.services.investigation.investigation_query_service import InvestigationQueryService
from app.services.investigation.correlation_analysis_service import CorrelationAnalysisService
from app.services.investigation.ai_diagnosis_service import AIDiagnosisService
from app.services.investigation.recovery_strategy_service import RecoveryStrategyService
from app.services.investigation.synthetic_incident_service import SyntheticIncidentService

router = APIRouter(prefix="/investigations", tags=["investigations"])


# ── Investigation CRUD ──────────────────────────────────────────────────
@router.post("/", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation(
    body: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Create a new investigation."""
    svc = InvestigationService(db)
    investigation = await svc.create_investigation(body)
    return InvestigationResponse.model_validate(investigation)


@router.get("/", response_model=InvestigationListResponse)
async def list_investigations(
    incident_id: uuid.UUID | None = None,
    state: str | None = None,
    investigation_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> InvestigationListResponse:
    """List investigations with optional filters."""
    svc = InvestigationService(db)
    return await svc.list_investigations(
        incident_id=incident_id,
        state=state,
        status=investigation_status,
        page=page,
        page_size=page_size,
    )


@router.get("/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Get an investigation by ID."""
    svc = InvestigationService(db)
    investigation = await svc.get_investigation(investigation_id)
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return InvestigationResponse.model_validate(investigation)


@router.patch("/{investigation_id}", response_model=InvestigationResponse)
async def update_investigation(
    investigation_id: uuid.UUID,
    body: InvestigationUpdate,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Update an investigation."""
    svc = InvestigationService(db)
    try:
        investigation = await svc.update_investigation(investigation_id, body)
        if not investigation:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return InvestigationResponse.model_validate(investigation)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{investigation_id}/transition/{target_state}")
async def transition_investigation(
    investigation_id: uuid.UUID,
    target_state: str,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
) -> InvestigationResponse:
    """Transition an investigation to a new state."""
    svc = InvestigationService(db)
    try:
        investigation = await svc.transition(investigation_id, target_state, data)
        return InvestigationResponse.model_validate(investigation)
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Investigation Queries ───────────────────────────────────────────────
@router.get("/queries/{dimension}", response_model=list[QueryResult])
async def query_by_dimension(
    dimension: str,
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> list[QueryResult]:
    """Query failures by a specific dimension."""
    svc = InvestigationQueryService(db)
    return await svc.query_by_dimension(dimension, time_window_hours)


@router.get("/queries/all")
async def query_all_dimensions(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[QueryResult]]:
    """Query failures across all dimensions."""
    svc = InvestigationQueryService(db)
    return await svc.query_all_dimensions(time_window_hours)


@router.get("/queries/pattern")
async def query_failure_pattern(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query overall failure pattern."""
    svc = InvestigationQueryService(db)
    return await svc.query_failure_pattern(time_window_hours)


# ── Correlation Analysis ────────────────────────────────────────────────
@router.get("/correlations", response_model=list[CorrelationResult])
async def analyze_correlations(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> list[CorrelationResult]:
    """Analyze correlations across all dimensions."""
    svc = CorrelationAnalysisService(db)
    return await svc.analyze_correlations(time_window_hours)


@router.get("/correlations/top", response_model=list[CorrelationResult])
async def get_top_contributors(
    time_window_hours: int = Query(24, ge=1, le=168),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
) -> list[CorrelationResult]:
    """Get top contributors to payment failures."""
    svc = CorrelationAnalysisService(db)
    return await svc.get_top_contributors(time_window_hours, limit)


# ── AI Diagnosis ────────────────────────────────────────────────────────
@router.get("/diagnosis", response_model=DiagnosisOutput)
async def generate_diagnosis(
    time_window_hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisOutput:
    """Generate AI-powered diagnosis."""
    svc = AIDiagnosisService(db)
    return await svc.generate_diagnosis(time_window_hours)


@router.post("/diagnosis/correlate", response_model=DiagnosisOutput)
async def diagnose_from_correlation(
    correlation_results: list[CorrelationResult],
    failure_pattern: dict,
    db: AsyncSession = Depends(get_db),
) -> DiagnosisOutput:
    """Generate diagnosis from pre-computed correlation results."""
    svc = AIDiagnosisService(db)
    return await svc.diagnose_from_correlation(correlation_results, failure_pattern)


# ── Recovery Strategy ───────────────────────────────────────────────────
@router.post("/strategy")
async def generate_recovery_strategy(
    diagnosis: DiagnosisOutput,
    correlation_results: list[CorrelationResult] | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate recovery strategy from diagnosis."""
    svc = RecoveryStrategyService(db)
    strategy = svc.generate_strategy(diagnosis, correlation_results)
    return strategy.to_dict()


# ── Synthetic Incidents ─────────────────────────────────────────────────
@router.post("/synthetic/upi-degradation")
async def create_upi_degradation(
    affected_count: int = Query(50, ge=1),
    revenue_impact: int = Query(2500000, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create synthetic UPI degradation incident."""
    svc = SyntheticIncidentService(db)
    return await svc.create_upi_degradation_incident(affected_count, revenue_impact)


@router.post("/synthetic/bank-decline-spike")
async def create_bank_decline_spike(
    affected_bank: str = Query("HDFC"),
    affected_count: int = Query(75, ge=1),
    revenue_impact: int = Query(3750000, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create synthetic bank decline spike incident."""
    svc = SyntheticIncidentService(db)
    return await svc.create_bank_decline_spike_incident(affected_bank, affected_count, revenue_impact)


@router.post("/synthetic/gateway-timeout")
async def create_gateway_timeout(
    affected_gateway: str = Query("Razorpay"),
    affected_count: int = Query(100, ge=1),
    revenue_impact: int = Query(5000000, ge=0),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create synthetic gateway timeout incident."""
    svc = SyntheticIncidentService(db)
    return await svc.create_gateway_timeout_incident(affected_gateway, affected_count, revenue_impact)


@router.post("/synthetic/run-all")
async def run_all_synthetic_tests(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Run all synthetic incident tests."""
    svc = SyntheticIncidentService(db)
    return await svc.run_all_synthetic_tests()
