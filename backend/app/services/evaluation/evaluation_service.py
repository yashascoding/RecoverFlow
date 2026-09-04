from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import func, select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.agent_action import AgentAction, AgentActionStatus
from app.models.email_message import EmailMessage, EmailStatus
from app.models.payment import Payment, PaymentStatus
from app.models.policy_decision import PolicyDecision, PolicyOutcome
from app.models.recovery_attempt import RecoveryAttempt, RecoveryAttemptStatus
from app.schemas.evaluation import (
    AgentMetrics,
    AssignmentGroupMetrics,
    ControlGroupAssignRequest,
    ControlGroupAssignResponse,
    CostMetrics,
    EmailMetrics,
    EvaluationRunResponse,
    LiftResult,
    PolicyMetrics,
    RecoveryMetrics,
)

logger = get_logger(__name__)

# Estimated costs
AI_COST_PER_RUN_USD = 0.05
EMAIL_COST_PER_EMAIL_USD = 0.001


class EvaluationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_recovery_metrics(
        self, start_time: datetime, end_time: datetime, group: str | None = None
    ) -> RecoveryMetrics:
        query = select(Payment).where(
            and_(Payment.created_at >= start_time, Payment.created_at < end_time)
        )
        if group:
            query = query.where(Payment.assignment_group == group)

        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        total = len(payments)
        failed = [p for p in payments if p.status in (PaymentStatus.FAILED.value, PaymentStatus.RECOVERY_PENDING.value)]
        recovered = [p for p in payments if p.status == PaymentStatus.RECOVERED.value]

        total_recovered_revenue = sum(p.amount for p in recovered)
        total_revenue_at_risk = sum(p.amount for p in failed)

        recovery_rate = round((len(recovered) / len(failed) * 100), 2) if failed else 0.0

        return RecoveryMetrics(
            total_payments=total,
            total_failed=len(failed),
            total_recovered=len(recovered),
            recovery_rate=recovery_rate,
            recovered_revenue=total_recovered_revenue,
            revenue_at_risk=total_revenue_at_risk,
        )

    async def get_email_metrics(
        self, start_time: datetime, end_time: datetime, group: str | None = None
    ) -> EmailMetrics:
        query = select(EmailMessage).where(
            and_(
                EmailMessage.created_at >= start_time,
                EmailMessage.created_at < end_time,
                EmailMessage.direction == "outbound",
            )
        )
        result = await self.db.execute(query)
        emails = list(result.scalars().all())

        total = len(emails)
        sent = sum(1 for e in emails if e.status in (EmailStatus.SENT.value, EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value))
        delivered = sum(1 for e in emails if e.status in (EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value))
        opened = sum(1 for e in emails if e.status in (EmailStatus.OPENED.value, EmailStatus.CLICKED.value))
        clicked = sum(1 for e in emails if e.status == EmailStatus.CLICKED.value)

        # For converted, check recovery attempts with matching email messages
        converted_query = select(RecoveryAttempt).where(
            and_(
                RecoveryAttempt.created_at >= start_time,
                RecoveryAttempt.created_at < end_time,
                RecoveryAttempt.status == RecoveryAttemptStatus.CONVERTED.value,
            )
        )
        converted_result = await self.db.execute(converted_query)
        converted = len(converted_result.scalars().all())

        delivery_rate = round((delivered / sent * 100), 2) if sent else 0.0
        open_rate = round((opened / delivered * 100), 2) if delivered else 0.0
        click_rate = round((clicked / opened * 100), 2) if opened else 0.0
        conversion_rate = round((converted / sent * 100), 2) if sent else 0.0

        return EmailMetrics(
            total_sent=sent,
            total_delivered=delivered,
            total_opened=opened,
            total_clicked=clicked,
            total_converted=converted,
            delivery_rate=delivery_rate,
            open_rate=open_rate,
            click_rate=click_rate,
            conversion_rate=conversion_rate,
        )

    async def get_agent_metrics(
        self, start_time: datetime, end_time: datetime
    ) -> AgentMetrics:
        query = select(AgentRun).where(
            and_(AgentRun.created_at >= start_time, AgentRun.created_at < end_time)
        )
        result = await self.db.execute(query)
        runs = list(result.scalars().all())

        total = len(runs)
        successful = sum(1 for r in runs if r.status == AgentRunStatus.COMPLETED.value)
        failed = sum(1 for r in runs if r.status == AgentRunStatus.FAILED.value)

        # Tool errors from agent actions
        action_query = select(AgentAction).where(
            and_(
                AgentAction.created_at >= start_time,
                AgentAction.created_at < end_time,
            )
        )
        action_result = await self.db.execute(action_query)
        actions = list(action_result.scalars().all())
        tool_errors = sum(1 for a in actions if a.status == AgentActionStatus.FAILED.value)

        # Latency calculations
        latencies = []
        for r in runs:
            if r.started_at and r.completed_at:
                latency_ms = (r.completed_at - r.started_at).total_seconds() * 1000
                latencies.append(latency_ms)

        avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if latencies else 0.0

        success_rate = round((successful / total * 100), 2) if total else 0.0

        return AgentMetrics(
            total_runs=total,
            successful_runs=successful,
            failed_runs=failed,
            tool_errors=tool_errors,
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            success_rate=success_rate,
        )

    async def get_policy_metrics(
        self, start_time: datetime, end_time: datetime
    ) -> PolicyMetrics:
        query = select(PolicyDecision).where(
            and_(PolicyDecision.created_at >= start_time, PolicyDecision.created_at < end_time)
        )
        result = await self.db.execute(query)
        decisions = list(result.scalars().all())

        total = len(decisions)
        allowed = sum(1 for d in decisions if d.outcome == PolicyOutcome.APPROVED.value)
        blocked = sum(1 for d in decisions if d.outcome == PolicyOutcome.DENIED.value)
        deferred = sum(1 for d in decisions if d.outcome == PolicyOutcome.DEFERRED.value)
        human_review = sum(1 for d in decisions if d.outcome == PolicyOutcome.DEFERRED.value)

        compliance_rate = round(((allowed + blocked) / total * 100), 2) if total else 0.0
        violations = blocked  # blocked = policy violations

        return PolicyMetrics(
            total_decisions=total,
            allowed=allowed,
            blocked=blocked,
            human_review=human_review,
            deferred=deferred,
            compliance_rate=compliance_rate,
            violations=violations,
        )

    async def get_cost_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
        recovered_revenue: int,
    ) -> CostMetrics:
        agent_query = select(AgentRun).where(
            and_(AgentRun.created_at >= start_time, AgentRun.created_at < end_time)
        )
        agent_result = await self.db.execute(agent_query)
        agent_runs = len(list(agent_result.scalars().all()))

        email_query = select(EmailMessage).where(
            and_(
                EmailMessage.created_at >= start_time,
                EmailMessage.created_at < end_time,
                EmailMessage.direction == "outbound",
            )
        )
        email_result = await self.db.execute(email_query)
        emails_sent = len(list(email_result.scalars().all()))

        ai_cost = round(agent_runs * AI_COST_PER_RUN_USD, 4)
        email_cost = round(emails_sent * EMAIL_COST_PER_EMAIL_USD, 4)
        total_cost = round(ai_cost + email_cost, 4)

        recovered_revenue_usd = round(recovered_revenue / 100, 2)
        net_recovered = round(recovered_revenue_usd - total_cost, 2)
        roi = round((net_recovered / total_cost * 100), 2) if total_cost > 0 else 0.0

        return CostMetrics(
            ai_cost_usd=ai_cost,
            email_cost_usd=email_cost,
            total_cost_usd=total_cost,
            recovered_revenue_usd=recovered_revenue_usd,
            net_recovered_revenue_usd=net_recovered,
            roi=roi,
        )

    async def get_group_metrics(
        self, start_time: datetime, end_time: datetime, group: str
    ) -> AssignmentGroupMetrics:
        query = select(Payment).where(
            and_(
                Payment.created_at >= start_time,
                Payment.created_at < end_time,
                Payment.assignment_group == group,
            )
        )
        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        total = len(payments)
        failed = [p for p in payments if p.status in (PaymentStatus.FAILED.value, PaymentStatus.RECOVERY_PENDING.value)]
        recovered = [p for p in payments if p.status == PaymentStatus.RECOVERED.value]

        recovery_rate = round((len(recovered) / len(failed) * 100), 2) if failed else 0.0
        recovered_revenue = sum(p.amount for p in recovered)
        total_revenue = sum(p.amount for p in payments if p.status in (PaymentStatus.CAPTURED.value, PaymentStatus.RECOVERED.value))

        return AssignmentGroupMetrics(
            group=group,
            payment_count=total,
            failed_count=len(failed),
            recovered_count=len(recovered),
            recovery_rate=recovery_rate,
            recovered_revenue=recovered_revenue,
            total_revenue=total_revenue,
        )

    def calculate_lift(
        self,
        control: AssignmentGroupMetrics,
        ai: AssignmentGroupMetrics,
    ) -> LiftResult:
        lift_absolute = round(ai.recovery_rate - control.recovery_rate, 2)
        lift_percentage = round(
            ((ai.recovery_rate - control.recovery_rate) / control.recovery_rate * 100), 2
        ) if control.recovery_rate > 0 else 0.0

        # Simple significance check: need at least 30 samples per group
        is_significant = (
            control.payment_count >= 30
            and ai.payment_count >= 30
            and abs(lift_absolute) > 1.0
        )

        return LiftResult(
            control_recovery_rate=control.recovery_rate,
            ai_recovery_rate=ai.recovery_rate,
            lift_absolute=lift_absolute,
            lift_percentage=lift_percentage,
            control_payment_count=control.payment_count,
            ai_payment_count=ai.payment_count,
            control_recovered_revenue=control.recovered_revenue,
            ai_recovered_revenue=ai.recovered_revenue,
            is_statistically_significant=is_significant,
        )

    async def run_evaluation(
        self, time_window_hours: int = 168
    ) -> EvaluationRunResponse:
        now = datetime.now(timezone.utc)
        start_time = now - timedelta(hours=time_window_hours)

        recovery = await self.get_recovery_metrics(start_time, now)
        email = await self.get_email_metrics(start_time, now)
        agent = await self.get_agent_metrics(start_time, now)
        policy = await self.get_policy_metrics(start_time, now)
        cost = await self.get_cost_metrics(start_time, now, recovery.recovered_revenue)

        control_group = await self.get_group_metrics(start_time, now, "control")
        ai_group = await self.get_group_metrics(start_time, now, "ai")

        lift = self.calculate_lift(control_group, ai_group)

        return EvaluationRunResponse(
            recovery=recovery,
            email=email,
            agent=agent,
            policy=policy,
            cost=cost,
            control_group=control_group,
            ai_group=ai_group,
            lift=lift,
            time_window_hours=time_window_hours,
            evaluated_at=now,
        )

    async def assign_control_groups(
        self, request: ControlGroupAssignRequest
    ) -> ControlGroupAssignResponse:
        if request.payment_ids:
            query = select(Payment).where(Payment.razorpay_order_id.in_(request.payment_ids))
        else:
            query = select(Payment).where(Payment.assignment_group.is_(None))

        result = await self.db.execute(query)
        payments = list(result.scalars().all())

        control_count = 0
        ai_count = 0
        control_ratio = request.control_percentage / 100.0

        for payment in payments:
            if random.random() < control_ratio:
                payment.assignment_group = "control"
                control_count += 1
            else:
                payment.assignment_group = "ai"
                ai_count += 1

        await self.db.commit()

        total = control_count + ai_count
        actual_percentage = round((control_count / total * 100), 2) if total else 0.0

        return ControlGroupAssignResponse(
            total_assigned=total,
            control_count=control_count,
            ai_count=ai_count,
            control_percentage=actual_percentage,
        )
