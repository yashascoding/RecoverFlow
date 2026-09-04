from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RecoveryMetrics(BaseModel):
    total_payments: int = 0
    total_failed: int = 0
    total_recovered: int = 0
    recovery_rate: float = 0.0
    recovered_revenue: int = 0
    revenue_at_risk: int = 0


class EmailMetrics(BaseModel):
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_converted: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    conversion_rate: float = 0.0


class AgentMetrics(BaseModel):
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    tool_errors: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    success_rate: float = 0.0


class PolicyMetrics(BaseModel):
    total_decisions: int = 0
    allowed: int = 0
    blocked: int = 0
    human_review: int = 0
    deferred: int = 0
    compliance_rate: float = 0.0
    violations: int = 0


class CostMetrics(BaseModel):
    ai_cost_usd: float = 0.0
    email_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    recovered_revenue_usd: float = 0.0
    net_recovered_revenue_usd: float = 0.0
    roi: float = 0.0


class AssignmentGroupMetrics(BaseModel):
    group: Literal["control", "ai"]
    payment_count: int = 0
    failed_count: int = 0
    recovered_count: int = 0
    recovery_rate: float = 0.0
    recovered_revenue: int = 0
    total_revenue: int = 0


class LiftResult(BaseModel):
    control_recovery_rate: float = 0.0
    ai_recovery_rate: float = 0.0
    lift_absolute: float = 0.0
    lift_percentage: float = 0.0
    control_payment_count: int = 0
    ai_payment_count: int = 0
    control_recovered_revenue: int = 0
    ai_recovered_revenue: int = 0
    is_statistically_significant: bool = False


class ControlGroupAssignRequest(BaseModel):
    control_percentage: float = Field(default=10.0, ge=1.0, le=50.0, description="Percentage of payments in control group")
    payment_ids: list[str] | None = Field(default=None, description="Specific payment IDs to assign, or None for random")


class ControlGroupAssignResponse(BaseModel):
    total_assigned: int = 0
    control_count: int = 0
    ai_count: int = 0
    control_percentage: float = 0.0


class EvaluationRunRequest(BaseModel):
    time_window_hours: int = Field(default=168, ge=1, le=720, description="Time window in hours (default 7 days)")


class EvaluationRunResponse(BaseModel):
    recovery: RecoveryMetrics
    email: EmailMetrics
    agent: AgentMetrics
    policy: PolicyMetrics
    cost: CostMetrics
    control_group: AssignmentGroupMetrics
    ai_group: AssignmentGroupMetrics
    lift: LiftResult
    time_window_hours: int
    evaluated_at: datetime


class EvaluationDashboardResponse(BaseModel):
    recovery: RecoveryMetrics
    email: EmailMetrics
    agent: AgentMetrics
    policy: PolicyMetrics
    cost: CostMetrics
    control_group: AssignmentGroupMetrics
    ai_group: AssignmentGroupMetrics
    lift: LiftResult
    time_window_hours: int
    generated_at: datetime
