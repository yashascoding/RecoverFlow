from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.services.agents.state_machine import AgentState


@dataclass
class ToolCall:
    tool_name: str
    arguments: dict
    result: dict | None = None
    error: str | None = None
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
        }


@dataclass
class StageTrace:
    stage: AgentState
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_data: dict = field(default_factory=dict)
    output_data: dict | None = None
    error: str | None = None
    latency_ms: float = 0.0

    def complete(self, output: dict | None = None, error: str | None = None) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.output_data = output
        self.error = error
        self.latency_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def add_tool_call(self, call: ToolCall) -> None:
        self.tool_calls.append(call)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "latency_ms": round(self.latency_ms, 2),
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
        }


class AgentTrace:
    """Records the full lifecycle of an agent run: stage transitions, tool calls, latency."""

    def __init__(
        self,
        run_id: uuid.UUID | None = None,
        payment_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> None:
        self.run_id = run_id or uuid.uuid4()
        self.payment_id = payment_id
        self.customer_id = customer_id
        self.started_at = datetime.now(timezone.utc)
        self.completed_at: datetime | None = None
        self.current_state: AgentState = AgentState.OBSERVE
        self.stages: list[StageTrace] = []
        self._stage_map: dict[AgentState, StageTrace] = {}
        self._start_time = time.monotonic()

    def begin_stage(self, state: AgentState, input_data: dict | None = None) -> StageTrace:
        stage = StageTrace(stage=state, input_data=input_data or {})
        self.stages.append(stage)
        self._stage_map[state] = stage
        self.current_state = state
        return stage

    def complete_stage(
        self,
        state: AgentState,
        output: dict | None = None,
        error: str | None = None,
    ) -> StageTrace:
        stage = self._stage_map.get(state)
        if not stage:
            stage = self.begin_stage(state)
        stage.complete(output=output, error=error)
        return stage

    def record_tool_call(
        self,
        state: AgentState,
        tool_name: str,
        arguments: dict,
        result: dict | None = None,
        error: str | None = None,
        latency_ms: float = 0.0,
    ) -> ToolCall:
        call = ToolCall(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            error=error,
            latency_ms=latency_ms,
        )
        stage = self._stage_map.get(state)
        if stage:
            stage.add_tool_call(call)
        return call

    def complete(self, final_state: AgentState) -> None:
        self.completed_at = datetime.now(timezone.utc)
        self.current_state = final_state

    @property
    def total_latency_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return (datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000

    def to_dict(self) -> dict:
        return {
            "run_id": str(self.run_id),
            "payment_id": str(self.payment_id) if self.payment_id else None,
            "customer_id": str(self.customer_id) if self.customer_id else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_state": self.current_state.value,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "stages": [s.to_dict() for s in self.stages],
        }
