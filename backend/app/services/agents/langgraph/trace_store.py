from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ToolCallRecord:
    """Single tool invocation trace."""

    tool_name: str
    arguments: dict = field(default_factory=dict)
    result: dict | None = None
    error: str | None = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ActionRecord:
    """Single agent action trace (email, retry, escalate, etc.)."""

    action_type: str
    target: str | None = None
    payload: dict = field(default_factory=dict)
    status: str = "pending"
    result: dict | None = None
    error_message: str | None = None
    executed_at: datetime | None = None
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "action_type": self.action_type,
            "target": self.target,
            "payload": self.payload,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "latency_ms": round(self.latency_ms, 2),
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StageRecord:
    """Trace for a single graph stage."""

    stage: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    error: str | None = None
    latency_ms: float = 0.0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)

    def complete(self, output: dict | None = None, error: str | None = None) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.output_data = output
        self.error = error
        self.latency_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def to_dict(self) -> dict:
        return {
            "stage": self.stage,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
        }


@dataclass
class RunRecord:
    """Full trace for one agent run.  Mirrors the DB agent_runs table."""

    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    agent_type: str = "recovery"
    payment_id: str | None = None
    customer_id: str | None = None
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    error_message: str | None = None
    status: str = "pending"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    stages: list[StageRecord] = field(default_factory=list)
    actions: list[ActionRecord] = field(default_factory=list)

    def complete(self, status: str = "completed", error: str | None = None) -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = error

    @property
    def total_latency_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return (datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "agent_type": self.agent_type,
            "payment_id": self.payment_id,
            "customer_id": self.customer_id,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "stages": [s.to_dict() for s in self.stages],
            "actions": [a.to_dict() for a in self.actions],
        }


class TraceStore:
    """In-memory store for all agent runs.  Provides query methods."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    @property
    def runs(self) -> list[RunRecord]:
        return list(self._runs.values())

    def create_run(
        self,
        *,
        agent_type: str = "recovery",
        payment_id: str | None = None,
        customer_id: str | None = None,
        input_data: dict | None = None,
    ) -> RunRecord:
        run = RunRecord(
            agent_type=agent_type,
            payment_id=payment_id,
            customer_id=customer_id,
            input_data=input_data or {},
            status="running",
        )
        self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def get_by_payment(self, payment_id: str) -> list[RunRecord]:
        return [r for r in self._runs.values() if r.payment_id == payment_id]

    def get_by_customer(self, customer_id: str) -> list[RunRecord]:
        return [r for r in self._runs.values() if r.customer_id == customer_id]

    def get_failed(self) -> list[RunRecord]:
        return [r for r in self._runs.values() if r.status == "failed"]

    def get_completed(self) -> list[RunRecord]:
        return [r for r in self._runs.values() if r.status == "completed"]

    def count_total(self) -> int:
        return len(self._runs)

    def begin_stage(self, run_id: str, stage: str, input_data: dict | None = None) -> StageRecord | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        rec = StageRecord(stage=stage, input_data=input_data or {})
        run.stages.append(rec)
        return rec

    def complete_stage(
        self, run_id: str, stage: str, output: dict | None = None, error: str | None = None
    ) -> StageRecord | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        for s in reversed(run.stages):
            if s.stage == stage and s.completed_at is None:
                s.complete(output=output, error=error)
                return s
        return None

    def record_tool_call(
        self,
        run_id: str,
        stage: str,
        *,
        tool_name: str,
        arguments: dict | None = None,
        result: dict | None = None,
        error: str | None = None,
        latency_ms: float = 0.0,
    ) -> ToolCallRecord | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        for s in reversed(run.stages):
            if s.stage == stage:
                tc = ToolCallRecord(
                    tool_name=tool_name,
                    arguments=arguments or {},
                    result=result,
                    error=error,
                    latency_ms=latency_ms,
                )
                s.tool_calls.append(tc)
                return tc
        return None

    def record_action(
        self,
        run_id: str,
        *,
        action_type: str,
        target: str | None = None,
        payload: dict | None = None,
        status: str = "pending",
        result: dict | None = None,
        error_message: str | None = None,
        latency_ms: float = 0.0,
    ) -> ActionRecord | None:
        run = self._runs.get(run_id)
        if not run:
            return None
        action = ActionRecord(
            action_type=action_type,
            target=target,
            payload=payload or {},
            status=status,
            result=result,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        run.actions.append(action)
        return action
