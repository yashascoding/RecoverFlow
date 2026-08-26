import asyncio
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agents.recovery_agent import (
    AgentError,
    LLMResponseError,
    LLMTimeoutError,
    ToolTimeoutError,
    RecoveryAgent,
)
from app.services.agents.agent_trace import AgentTrace
from app.services.agents.state_machine import AgentState, AgentStateMachine


# ── Mock tools ──────────────────────────────────────────────────────────────

class MockTool:
    def __init__(self, name: str, return_value: dict | None = None, error: Exception | None = None, delay: float = 0):
        self.name = name
        self._return_value = return_value or {}
        self._error = error
        self._delay = delay
        self.call_count = 0
        self.last_kwargs = {}

    async def execute(self, **kwargs: Any) -> dict:
        self.call_count += 1
        self.last_kwargs = kwargs
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._error:
            raise self._error
        return self._return_value


def _make_agent(
    tools: list | None = None,
    llm_return: dict | None = None,
    llm_error: Exception | None = None,
    llm_delay: float = 0,
    tool_timeout: float = 10.0,
    llm_timeout: float = 30.0,
) -> RecoveryAgent:
    db = AsyncMock()

    if tools is None:
        tools = [
            MockTool("fetch_customer", {"id": "c1", "email": "a@b.com", "name": "Test", "status": "active"}),
            MockTool("fetch_payment", {"id": "p1", "order_id": "order_abc", "amount": 5000, "status": "failed", "failure_reason": "UPI timeout", "customer_email": "a@b.com", "customer_id": "c1"}),
            MockTool("check_consent", {"has_consent": True, "channel": "email"}),
            MockTool("diagnose_failure", {"category": "upi_timeout", "strategy": "instant_retry", "reason": "timeout"}),
        ]

    async def mock_llm(prompt: str) -> dict:
        if llm_delay > 0:
            await asyncio.sleep(llm_delay)
        if llm_error:
            raise llm_error
        return llm_return or {
            "diagnosis": "UPI timeout detected",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "Transient UPI timeout",
            "risk_level": "LOW",
        }

    agent = RecoveryAgent(
        db=db,
        llm_call=mock_llm,
        tools=tools,
        tool_timeout=tool_timeout,
        llm_timeout=llm_timeout,
    )
    return agent


# ── Happy path ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestHappyPath:
    async def test_full_pipeline(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is True
        assert result["state"] == "completed"
        assert "trace" in result
        assert result["trace"]["current_state"] == "completed"

    async def test_trace_has_all_stages(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        stages = [s["stage"] for s in result["trace"]["stages"]]
        assert stages == ["observe", "investigate", "diagnose", "plan"]

    async def test_trace_records_tool_calls(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        all_tool_calls = []
        for stage in result["trace"]["stages"]:
            all_tool_calls.extend(stage["tool_calls"])
        tool_names = [tc["tool_name"] for tc in all_tool_calls]
        assert "fetch_customer" in tool_names
        assert "fetch_payment" in tool_names
        assert "check_consent" in tool_names
        assert "diagnose_failure" in tool_names
        assert "llm_call" in tool_names

    async def test_trace_has_latency(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["trace"]["total_latency_ms"] >= 0

    async def test_tool_latency_recorded(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        for stage in result["trace"]["stages"]:
            for tc in stage["tool_calls"]:
                assert tc["latency_ms"] >= 0


# ── Missing customer ────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMissingCustomer:
    async def test_customer_not_found_tool_error(self):
        tools = [
            MockTool("fetch_customer", error=Exception("Customer not found: c999")),
            MockTool("fetch_payment", {"id": "p1", "order_id": "o1", "amount": 5000, "status": "failed", "failure_reason": "timeout", "customer_email": "a@b.com"}),
            MockTool("check_consent", {"has_consent": False}),
            MockTool("diagnose_failure", {"category": "unknown"}),
        ]
        agent = _make_agent(tools=tools)
        result = await agent.run({"payment_id": "p1", "customer_id": "c999"})
        assert result["success"] is False
        assert "Customer not found" in result["error"]

    async def test_customer_not_found_in_observe(self):
        tools = [
            MockTool("fetch_customer", error=ValueError("not found")),
            MockTool("fetch_payment", {"id": "p1"}),
        ]
        agent = _make_agent(tools=tools)
        result = await agent.run({"customer_id": "c999"})
        assert result["success"] is False
        assert result["state"] == "failed"


# ── Missing payment ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMissingPayment:
    async def test_payment_not_found_tool_error(self):
        tools = [
            MockTool("fetch_customer", {"id": "c1", "email": "a@b.com", "name": "Test", "status": "active"}),
            MockTool("fetch_payment", error=Exception("Payment not found: p999")),
        ]
        agent = _make_agent(tools=tools)
        result = await agent.run({"payment_id": "p999", "customer_id": "c1"})
        assert result["success"] is False
        assert "Payment not found" in result["error"]

    async def test_no_payment_or_customer(self):
        agent = _make_agent()
        result = await agent.run({})
        assert result["success"] is True
        stages = result["trace"]["stages"]
        observe = stages[0]
        assert observe["output_data"]["customer"] is None
        assert observe["output_data"]["payment"] is None


# ── Invalid state ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestInvalidState:
    async def test_tool_returns_invalid_state_still_succeeds(self):
        tools = [
            MockTool("fetch_customer", {"id": "c1", "email": "a@b.com", "name": "T", "status": "active"}),
            MockTool("fetch_payment", {"id": "p1", "order_id": "o1", "amount": 5000, "status": "captured", "failure_reason": None, "customer_email": "a@b.com", "customer_id": "c1"}),
            MockTool("check_consent", {"has_consent": True}),
            MockTool("diagnose_failure", {"category": "unknown"}),
        ]
        agent = _make_agent(tools=tools)
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is True
        investigate_out = result["trace"]["stages"][1]["output_data"]
        assert investigate_out["payment_status"] == "captured"


# ── LLM timeout ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestLLMTimeout:
    async def test_llm_timeout_returns_failure(self):
        agent = _make_agent(llm_delay=0.5, llm_timeout=0.01)
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    async def test_llm_timeout_records_in_trace(self):
        agent = _make_agent(llm_delay=0.5, llm_timeout=0.01)
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        diagnose_stage = result["trace"]["stages"][2]
        assert diagnose_stage["error"] is not None

    async def test_llm_timeout_tool_call_recorded(self):
        agent = _make_agent(llm_delay=0.5, llm_timeout=0.01)
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        diagnose_stage = result["trace"]["stages"][2]
        llm_calls = [tc for tc in diagnose_stage["tool_calls"] if tc["tool_name"] == "llm_call"]
        assert len(llm_calls) == 1
        assert llm_calls[0]["error"] == "timeout"


# ── Malformed LLM output ────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMalformedLLMOutput:
    async def test_missing_required_fields(self):
        agent = _make_agent(llm_return={"diagnosis": "test"})
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is False
        assert "Malformed" in result["error"]

    async def test_invalid_confidence(self):
        agent = _make_agent(llm_return={
            "diagnosis": "test",
            "confidence": 2.0,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        })
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is False

    async def test_invalid_action(self):
        agent = _make_agent(llm_return={
            "diagnosis": "test",
            "confidence": 0.5,
            "recommended_action": "INVALID_ACTION",
            "reason": "test",
            "risk_level": "LOW",
        })
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is False

    async def test_llm_returns_non_dict(self):
        async def bad_llm(prompt: str) -> str:
            return "not a dict"

        db = AsyncMock()
        agent = RecoveryAgent(db=db, llm_call=bad_llm)
        result = await agent.run({"payment_id": "p1"})
        assert result["success"] is False

    async def test_malformed_output_recorded_in_trace(self):
        agent = _make_agent(llm_return={"only": "diagnosis"})
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        diagnose_stage = result["trace"]["stages"][2]
        assert diagnose_stage["error"] is not None
        assert "Malformed" in diagnose_stage["error"]


# ── Tool timeout ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestToolTimeout:
    async def test_tool_timeout_returns_failure(self):
        tools = [
            MockTool("fetch_customer", {"id": "c1"}, delay=1.0),
            MockTool("fetch_payment", {"id": "p1"}, delay=1.0),
        ]
        agent = _make_agent(tools=tools, tool_timeout=0.01)
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["success"] is False
        assert "timed out" in result["error"].lower()

    async def test_tool_timeout_recorded_in_trace(self):
        tools = [
            MockTool("fetch_customer", {"id": "c1"}, delay=1.0),
        ]
        agent = _make_agent(tools=tools, tool_timeout=0.01)
        result = await agent.run({"customer_id": "c1"})
        observe_stage = result["trace"]["stages"][0]
        timeout_calls = [tc for tc in observe_stage["tool_calls"] if tc["error"] == "timeout"]
        assert len(timeout_calls) == 1


# ── Trace structure ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestTraceStructure:
    async def test_trace_has_run_id(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["trace"]["run_id"] is not None

    async def test_trace_has_payment_id(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "550e8400-e29b-41d4-a716-446655440000", "customer_id": "c1"})
        assert result["trace"]["payment_id"] == "550e8400-e29b-41d4-a716-446655440000"

    async def test_trace_has_started_at(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["trace"]["started_at"] is not None

    async def test_trace_has_completed_at(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        assert result["trace"]["completed_at"] is not None

    async def test_each_stage_has_input_and_output(self):
        agent = _make_agent()
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        for stage in result["trace"]["stages"]:
            assert "input_data" in stage
            assert "output_data" in stage or "error" in stage


# ── Action planning ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestActionPlanning:
    async def test_high_risk_adds_review_flag(self):
        agent = _make_agent(llm_return={
            "diagnosis": "Fraud suspected",
            "confidence": 0.95,
            "recommended_action": "ESCALATE_TO_HUMAN",
            "reason": "Suspicious pattern",
            "risk_level": "HIGH",
        })
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        plan_out = result["trace"]["stages"][3]["output_data"]
        actions = plan_out["recommended_actions"]
        assert any(a["type"] == "escalate" for a in actions)
        assert any(a["type"] == "flag_for_review" for a in actions)

    async def test_low_risk_no_review_flag(self):
        agent = _make_agent(llm_return={
            "diagnosis": "Simple timeout",
            "confidence": 0.8,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "Transient",
            "risk_level": "LOW",
        })
        result = await agent.run({"payment_id": "p1", "customer_id": "c1"})
        plan_out = result["trace"]["stages"][3]["output_data"]
        actions = plan_out["recommended_actions"]
        assert not any(a["type"] == "flag_for_review" for a in actions)
