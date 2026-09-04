from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.evaluation import (
    ControlGroupAssignRequest,
    ControlGroupAssignResponse,
    EvaluationDashboardResponse,
    EvaluationRunRequest,
    EvaluationRunResponse,
)
from app.services.evaluation.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/dashboard", response_model=EvaluationDashboardResponse)
async def get_evaluation_dashboard(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
) -> EvaluationDashboardResponse:
    svc = EvaluationService(db)
    result = await svc.run_evaluation(time_window_hours=time_window_hours)

    return EvaluationDashboardResponse(
        recovery=result.recovery,
        email=result.email,
        agent=result.agent,
        policy=result.policy,
        cost=result.cost,
        control_group=result.control_group,
        ai_group=result.ai_group,
        lift=result.lift,
        time_window_hours=result.time_window_hours,
        generated_at=result.evaluated_at,
    )


@router.post("/run", response_model=EvaluationRunResponse)
async def run_evaluation(
    body: EvaluationRunRequest,
    db: AsyncSession = Depends(get_db),
) -> EvaluationRunResponse:
    svc = EvaluationService(db)
    return await svc.run_evaluation(time_window_hours=body.time_window_hours)


@router.post("/control-group/assign", response_model=ControlGroupAssignResponse)
async def assign_control_group(
    body: ControlGroupAssignRequest,
    db: AsyncSession = Depends(get_db),
) -> ControlGroupAssignResponse:
    svc = EvaluationService(db)
    return await svc.assign_control_groups(body)


@router.get("/recovery")
async def get_recovery_metrics(
    time_window_hours: int = Query(168, ge=1, le=720),
    group: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    return await svc.get_recovery_metrics(start, now, group)


@router.get("/email")
async def get_email_metrics(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    return await svc.get_email_metrics(start, now)


@router.get("/agent")
async def get_agent_metrics(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    return await svc.get_agent_metrics(start, now)


@router.get("/policy")
async def get_policy_metrics(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    return await svc.get_policy_metrics(start, now)


@router.get("/cost")
async def get_cost_metrics(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    recovery = await svc.get_recovery_metrics(start, now)
    return await svc.get_cost_metrics(start, now, recovery.recovered_revenue)


@router.get("/lift")
async def get_lift(
    time_window_hours: int = Query(168, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
):
    svc = EvaluationService(db)
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=time_window_hours)
    control = await svc.get_group_metrics(start, now, "control")
    ai = await svc.get_group_metrics(start, now, "ai")
    return svc.calculate_lift(control, ai)
