from __future__ import annotations

import enum
from typing import Any, TypedDict

from pydantic import BaseModel, Field


# ── Graph stage enum ────────────────────────────────────────────────────────

class Stage(str, enum.Enum):
    OBSERVE = "observe"
    INVESTIGATE = "investigate"
    DIAGNOSE = "diagnose"
    PLAN = "plan"
    COMPLETED = "completed"
    FAILED = "failed"


# ── LLM diagnosis output ───────────────────────────────────────────────────

class DiagnosisOutput(BaseModel):
    diagnosis: str = Field(..., min_length=1, max_length=2000)
    confidence: float = Field(..., ge=0.0, le=1.0)
    recommended_action: str = Field(..., min_length=1)
    reason: str = Field(..., min_length=1, max_length=2000)
    risk_level: str = Field(..., pattern=r"^(LOW|MEDIUM|HIGH)$")


# ── Tool call record (embedded in state) ────────────────────────────────────

class ToolCallRecord(TypedDict, total=False):
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    error: str
    latency_ms: float


# ── Custom reducer for tool_calls ──────────────────────────────────────────

def _append_tool_calls(left: list[dict], right: list[dict]) -> list[dict]:
    """Reducer that appends tool call records from each node."""
    return left + right


# ── LangGraph state ─────────────────────────────────────────────────────────

from typing import Annotated

class RecoveryState(TypedDict, total=False):
    """Mutable state passed through every LangGraph node."""

    # ── identifiers ─────────────────────────────────────────────────────
    run_id: str
    payment_id: str
    customer_id: str

    # ── control ─────────────────────────────────────────────────────────
    stage: Stage
    error: str | None

    # ── observe output ──────────────────────────────────────────────────
    customer_data: dict[str, Any]
    payment_data: dict[str, Any]

    # ── investigate output ──────────────────────────────────────────────
    consent_data: dict[str, Any]
    failure_diagnosis: dict[str, Any]

    # ── diagnose output ─────────────────────────────────────────────────
    llm_diagnosis: dict[str, Any]
    diagnosis_raw: dict[str, Any]

    # ── plan output ─────────────────────────────────────────────────────
    planned_actions: list[dict[str, Any]]

    # ── trace — each node appends its tool calls via reducer ─────────────
    tool_calls: Annotated[list[dict[str, Any]], _append_tool_calls]
    stage_latencies_ms: dict[str, float]
    total_latency_ms: float

    # ── custom LLM callable ─────────────────────────────────────────────
    _llm_call: Any
    _tools: dict[str, Any]
