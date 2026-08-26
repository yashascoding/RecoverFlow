import pytest

from app.services.agents.langgraph.state import DiagnosisOutput, RecoveryState, Stage
from app.services.agents.langgraph.trace_store import (
    ActionRecord,
    RunRecord,
    StageRecord,
    ToolCallRecord,
    TraceStore,
)
from app.services.agents.langgraph.graph import RecoveryGraph
from app.services.agents.langgraph.nodes import _safe_uuid


# ═══════════════════════════════════════════════════════════════════════════
# State
# ═══════════════════════════════════════════════════════════════════════════

class TestStageEnum:
    def test_all_values(self):
        values = [s.value for s in Stage]
        assert "observe" in values
        assert "investigate" in values
        assert "diagnose" in values
        assert "plan" in values
        assert "completed" in values
        assert "failed" in values

    def test_string_comparison(self):
        assert Stage.OBSERVE.value == "observe"


class TestDiagnosisOutput:
    def test_valid(self):
        d = DiagnosisOutput(
            diagnosis="UPI timeout",
            confidence=0.9,
            recommended_action="RETRY_PAYMENT",
            reason="Transient failure",
            risk_level="LOW",
        )
        assert d.confidence == 0.9
        assert d.risk_level == "LOW"

    def test_invalid_risk_level(self):
        with pytest.raises(Exception):
            DiagnosisOutput(
                diagnosis="test",
                confidence=0.5,
                recommended_action="EMAIL_PAYMENT_LINK",
                reason="test",
                risk_level="EXTREME",
            )

    def test_confidence_out_of_range(self):
        with pytest.raises(Exception):
            DiagnosisOutput(
                diagnosis="test",
                confidence=2.0,
                recommended_action="EMAIL_PAYMENT_LINK",
                reason="test",
                risk_level="LOW",
            )


class TestSafeUuid:
    def test_valid_uuid(self):
        import uuid
        uid = str(uuid.uuid4())
        assert _safe_uuid(uid) == uid

    def test_none(self):
        assert _safe_uuid(None) is None

    def test_empty(self):
        assert _safe_uuid("") is None

    def test_invalid(self):
        assert _safe_uuid("not-a-uuid") is None


# ═══════════════════════════════════════════════════════════════════════════
# Trace Store — ToolCallRecord
# ═══════════════════════════════════════════════════════════════════════════

class TestToolCallRecord:
    def test_basic(self):
        tc = ToolCallRecord(tool_name="fetch_customer", arguments={"id": "c1"}, latency_ms=12.5)
        assert tc.tool_name == "fetch_customer"
        assert tc.latency_ms == 12.5

    def test_to_dict(self):
        tc = ToolCallRecord(
            tool_name="fetch_payment",
            arguments={"payment_id": "p1"},
            result={"status": "captured"},
            latency_ms=5.3,
        )
        d = tc.to_dict()
        assert d["tool_name"] == "fetch_payment"
        assert d["result"]["status"] == "captured"
        assert d["error"] is None

    def test_error_record(self):
        tc = ToolCallRecord(tool_name="llm_call", error="timeout", latency_ms=30000)
        d = tc.to_dict()
        assert d["error"] == "timeout"
        assert d["result"] is None


# ═══════════════════════════════════════════════════════════════════════════
# Trace Store — ActionRecord
# ═══════════════════════════════════════════════════════════════════════════

class TestActionRecord:
    def test_basic(self):
        a = ActionRecord(action_type="send_email", target="cust_1")
        assert a.action_type == "send_email"
        assert a.status == "pending"

    def test_to_dict(self):
        a = ActionRecord(
            action_type="retry_payment",
            payload={"delay_seconds": 60},
            status="executed",
            latency_ms=150.0,
        )
        d = a.to_dict()
        assert d["action_type"] == "retry_payment"
        assert d["status"] == "executed"
        assert d["payload"]["delay_seconds"] == 60


# ═══════════════════════════════════════════════════════════════════════════
# Trace Store — StageRecord
# ═══════════════════════════════════════════════════════════════════════════

class TestStageRecord:
    def test_incomplete(self):
        s = StageRecord(stage="observe")
        assert s.completed_at is None
        assert s.latency_ms == 0.0

    def test_complete(self):
        s = StageRecord(stage="observe")
        s.complete(output={"key": "value"})
        assert s.completed_at is not None
        assert s.output_data == {"key": "value"}
        assert s.latency_ms >= 0

    def test_complete_with_error(self):
        s = StageRecord(stage="diagnose")
        s.complete(error="LLM timeout")
        assert s.error == "LLM timeout"

    def test_to_dict(self):
        s = StageRecord(stage="investigate", input_data={"a": 1})
        s.complete(output={"b": 2})
        d = s.to_dict()
        assert d["stage"] == "investigate"
        assert d["input_data"] == {"a": 1}
        assert d["output_data"] == {"b": 2}


# ═══════════════════════════════════════════════════════════════════════════
# Trace Store — RunRecord
# ═══════════════════════════════════════════════════════════════════════════

class TestRunRecord:
    def test_initial_status(self):
        r = RunRecord()
        assert r.status == "pending"
        assert r.completed_at is None

    def test_complete(self):
        r = RunRecord()
        r.complete(status="completed")
        assert r.status == "completed"
        assert r.completed_at is not None

    def test_total_latency(self):
        r = RunRecord()
        r.complete()
        assert r.total_latency_ms >= 0

    def test_to_dict(self):
        r = RunRecord(run_id="abc123", payment_id="p1", customer_id="c1")
        r.stages.append(StageRecord(stage="observe"))
        r.actions.append(ActionRecord(action_type="send_email"))
        d = r.to_dict()
        assert d["run_id"] == "abc123"
        assert len(d["stages"]) == 1
        assert len(d["actions"]) == 1


# ═══════════════════════════════════════════════════════════════════════════
# TraceStore — CRUD + queries
# ═══════════════════════════════════════════════════════════════════════════

class TestTraceStoreCreate:
    def test_create_run(self):
        store = TraceStore()
        run = store.create_run(agent_type="recovery", payment_id="p1")
        assert run.run_id is not None
        assert run.agent_type == "recovery"
        assert run.payment_id == "p1"
        assert run.status == "running"

    def test_stores_run(self):
        store = TraceStore()
        store.create_run()
        assert store.count_total() == 1

    def test_multiple_runs(self):
        store = TraceStore()
        store.create_run(payment_id="p1")
        store.create_run(payment_id="p2")
        assert store.count_total() == 2


class TestTraceStoreQueries:
    def _setup(self):
        store = TraceStore()
        r1 = store.create_run(payment_id="pay_1", customer_id="cust_1")
        r2 = store.create_run(payment_id="pay_2", customer_id="cust_1")
        r3 = store.create_run(payment_id="pay_1", customer_id="cust_2")
        r2.complete(status="failed", error="timeout")
        return store, r1, r2, r3

    def test_get_run(self):
        store, r1, _, _ = self._setup()
        found = store.get_run(r1.run_id)
        assert found is r1

    def test_get_run_not_found(self):
        store = TraceStore()
        assert store.get_run("nonexistent") is None

    def test_get_by_payment(self):
        store, _, _, _ = self._setup()
        runs = store.get_by_payment("pay_1")
        assert len(runs) == 2

    def test_get_by_customer(self):
        store, _, _, _ = self._setup()
        runs = store.get_by_customer("cust_1")
        assert len(runs) == 2

    def test_get_failed(self):
        store, _, r2, _ = self._setup()
        failed = store.get_failed()
        assert len(failed) == 1
        assert failed[0].run_id == r2.run_id

    def test_get_completed(self):
        store, r1, _, _ = self._setup()
        r1.complete(status="completed")
        completed = store.get_completed()
        assert len(completed) == 1


class TestTraceStoreStageTracking:
    def test_begin_and_complete_stage(self):
        store = TraceStore()
        run = store.create_run()
        stage = store.begin_stage(run.run_id, "observe", input_data={"x": 1})
        assert stage is not None
        assert stage.stage == "observe"

        completed = store.complete_stage(run.run_id, "observe", output={"y": 2})
        assert completed is not None
        assert completed.completed_at is not None
        assert completed.output_data == {"y": 2}

    def test_complete_nonexistent_run(self):
        store = TraceStore()
        assert store.complete_stage("bad_id", "observe") is None

    def test_complete_nonexistent_stage(self):
        store = TraceStore()
        run = store.create_run()
        store.begin_stage(run.run_id, "observe")
        # Try to complete a stage that doesn't exist
        result = store.complete_stage(run.run_id, "diagnose")
        assert result is None


class TestTraceStoreToolCalls:
    def test_record_tool_call(self):
        store = TraceStore()
        run = store.create_run()
        store.begin_stage(run.run_id, "observe")

        tc = store.record_tool_call(
            run.run_id, "observe",
            tool_name="fetch_customer",
            arguments={"customer_id": "c1"},
            result={"email": "test@example.com"},
            latency_ms=15.3,
        )
        assert tc is not None
        assert tc.tool_name == "fetch_customer"
        assert tc.result["email"] == "test@example.com"

    def test_tool_call_error(self):
        store = TraceStore()
        run = store.create_run()
        store.begin_stage(run.run_id, "observe")

        tc = store.record_tool_call(
            run.run_id, "observe",
            tool_name="fetch_payment",
            error="not found",
        )
        assert tc.error == "not found"

    def test_tool_call_bad_run(self):
        store = TraceStore()
        assert store.record_tool_call("bad", "observe", tool_name="x") is None


class TestTraceStoreActions:
    def test_record_action(self):
        store = TraceStore()
        run = store.create_run()

        action = store.record_action(
            run.run_id,
            action_type="send_email",
            target="cust_1",
            payload={"template": "PAYMENT_RECOVERY"},
        )
        assert action is not None
        assert action.action_type == "send_email"
        assert len(run.actions) == 1

    def test_record_action_bad_run(self):
        store = TraceStore()
        assert store.record_action("bad", action_type="x") is None


# ═══════════════════════════════════════════════════════════════════════════
# RecoveryGraph — structure
# ═══════════════════════════════════════════════════════════════════════════

class TestRecoveryGraphStructure:
    def test_builds(self):
        g = RecoveryGraph()
        assert g._compiled is not None

    def test_has_trace_store(self):
        g = RecoveryGraph()
        assert isinstance(g.trace_store, TraceStore)

    def test_stage_tool_map(self):
        g = RecoveryGraph()
        assert "fetch_customer" in g._stage_tool_map["observe"]
        assert "check_consent" in g._stage_tool_map["investigate"]
        assert "llm_call" in g._stage_tool_map["diagnose"]


# ═══════════════════════════════════════════════════════════════════════════
# RecoveryGraph — full pipeline execution
# ═══════════════════════════════════════════════════════════════════════════

class _FakeFetchCustomer:
    name = "fetch_customer"
    async def execute(self, **kw):
        return {"id": "c1", "email": "test@example.com", "name": "Test User"}


class _FakeFetchPayment:
    name = "fetch_payment"
    async def execute(self, **kw):
        return {"id": "p1", "status": "failed", "amount": 500, "failure_reason": "UPI timeout"}


class _FakeCheckConsent:
    name = "check_consent"
    async def execute(self, **kw):
        return {"has_consent": True, "channel": "email"}


class _FakeDiagnoseFailure:
    name = "diagnose_failure"
    async def execute(self, **kw):
        return {"category": "upi_timeout", "strategy": "instant_retry", "reason": "UPI timeout"}


class TestRecoveryGraphExecution:
    @pytest.fixture
    def tools(self):
        return {
            "fetch_customer": _FakeFetchCustomer(),
            "fetch_payment": _FakeFetchPayment(),
            "check_consent": _FakeCheckConsent(),
            "diagnose_failure": _FakeDiagnoseFailure(),
        }

    @pytest.mark.asyncio
    async def test_full_pipeline_no_llm(self, tools):
        g = RecoveryGraph()
        result = await g.run(
            payment_id="p1",
            customer_id="c1",
            tools=tools,
        )

        assert result["success"] is True
        assert result["status"] == "completed"
        assert result["run_id"] is not None
        assert result["diagnosis"] is not None
        assert result["planned_actions"] is not None
        assert len(result["planned_actions"]) > 0
        assert result["total_latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_full_pipeline_with_llm(self, tools):
        async def fake_llm(prompt: str) -> dict:
            return {
                "diagnosis": "UPI timeout — retry",
                "confidence": 0.9,
                "recommended_action": "RETRY_PAYMENT",
                "reason": "Transient UPI timeout",
                "risk_level": "LOW",
            }

        g = RecoveryGraph()
        result = await g.run(
            payment_id="p1",
            customer_id="c1",
            tools=tools,
            llm_call=fake_llm,
        )

        assert result["success"] is True
        assert result["diagnosis"]["recommended_action"] == "RETRY_PAYMENT"
        assert result["diagnosis"]["risk_level"] == "LOW"
        actions = result["planned_actions"]
        assert any(a["type"] == "retry_payment" for a in actions)

    @pytest.mark.asyncio
    async def test_trace_store_has_runs(self, tools):
        g = RecoveryGraph()
        await g.run(payment_id="p1", customer_id="c1", tools=tools)

        assert g.trace_store.count_total() == 1
        run = g.trace_store.runs[0]
        assert run.status == "completed"
        assert len(run.actions) > 0

    @pytest.mark.asyncio
    async def test_trace_captures_tool_calls(self, tools):
        g = RecoveryGraph()
        result = await g.run(payment_id="p1", customer_id="c1", tools=tools)

        run = g.trace_store.get_run(result["run_id"])
        # Should have observe + investigate stages
        stage_names = [s.stage for s in run.stages]
        assert "observe" in stage_names or "investigate" in stage_names


class TestRecoveryGraphWithLLM:
    @pytest.mark.asyncio
    async def test_llm_high_risk_adds_flag(self):
        tools = {
            "fetch_customer": _FakeFetchCustomer(),
            "fetch_payment": _FakeFetchPayment(),
            "check_consent": _FakeCheckConsent(),
            "diagnose_failure": _FakeDiagnoseFailure(),
        }

        async def high_risk_llm(prompt: str) -> dict:
            return {
                "diagnosis": "Fraud check triggered",
                "confidence": 0.95,
                "recommended_action": "ESCALATE_TO_HUMAN",
                "reason": "Suspicious activity",
                "risk_level": "HIGH",
            }

        g = RecoveryGraph()
        result = await g.run(
            payment_id="p1", customer_id="c1",
            tools=tools, llm_call=high_risk_llm,
        )

        actions = result["planned_actions"]
        assert any(a["type"] == "escalate" for a in actions)
        assert any(a["type"] == "flag_for_review" for a in actions)

    @pytest.mark.asyncio
    async def test_llm_block_recovery(self):
        tools = {
            "fetch_customer": _FakeFetchCustomer(),
            "fetch_payment": _FakeFetchPayment(),
            "check_consent": _FakeCheckConsent(),
            "diagnose_failure": _FakeDiagnoseFailure(),
        }

        async def block_llm(prompt: str) -> dict:
            return {
                "diagnosis": "User confirmed cancellation",
                "confidence": 1.0,
                "recommended_action": "BLOCK_RECOVERY",
                "reason": "Customer explicitly cancelled",
                "risk_level": "LOW",
            }

        g = RecoveryGraph()
        result = await g.run(
            payment_id="p1", customer_id="c1",
            tools=tools, llm_call=block_llm,
        )

        actions = result["planned_actions"]
        assert any(a["type"] == "block" for a in actions)


class TestRecoveryGraphErrorHandling:
    @pytest.mark.asyncio
    async def test_llm_timeout(self):
        tools = {
            "fetch_customer": _FakeFetchCustomer(),
            "fetch_payment": _FakeFetchPayment(),
            "check_consent": _FakeCheckConsent(),
            "diagnose_failure": _FakeDiagnoseFailure(),
        }

        async def timeout_llm(prompt: str) -> dict:
            raise TimeoutError("LLM timed out")

        g = RecoveryGraph()
        result = await g.run(
            payment_id="p1", customer_id="c1",
            tools=tools, llm_call=timeout_llm,
        )

        # Graph should still complete with fallback diagnosis
        assert result["success"] is True
        assert result["diagnosis"] is not None

    @pytest.mark.asyncio
    async def test_empty_tools_still_works(self):
        g = RecoveryGraph()
        result = await g.run(payment_id="p1", customer_id="c1", tools={})

        assert result["success"] is True
        # Should have deterministic diagnosis from empty failure_diagnosis
        assert result["diagnosis"] is not None

    @pytest.mark.asyncio
    async def test_run_id_in_trace(self):
        tools = {"fetch_customer": _FakeFetchCustomer(), "fetch_payment": _FakeFetchPayment()}
        g = RecoveryGraph()
        result = await g.run(payment_id="p1", customer_id="c1", tools=tools)

        assert result["run_id"] is not None
        run = g.trace_store.get_run(result["run_id"])
        assert run is not None
        assert run.payment_id == "p1"
        assert run.customer_id == "c1"


# ═══════════════════════════════════════════════════════════════════════════
# Integration: LangGraph + PolicyDecisionLogger
# ═══════════════════════════════════════════════════════════════════════════

class TestLangGraphWithPolicyLogger:
    @pytest.mark.asyncio
    async def test_decision_logged_after_graph(self):
        from app.services.policy.policy_decision_logger import DecisionResult, PolicyDecisionLogger

        tools = {
            "fetch_customer": _FakeFetchCustomer(),
            "fetch_payment": _FakeFetchPayment(),
            "check_consent": _FakeCheckConsent(),
            "diagnose_failure": _FakeDiagnoseFailure(),
        }

        g = RecoveryGraph()
        result = await g.run(payment_id="p1", customer_id="c1", tools=tools)

        logger = PolicyDecisionLogger()
        diagnosis = result.get("diagnosis") or {}
        action = diagnosis.get("recommended_action", "EMAIL_PAYMENT_LINK")
        risk = diagnosis.get("risk_level", "HIGH")

        if risk == "HIGH":
            dr = DecisionResult.HUMAN_REVIEW
        elif action == "BLOCK_RECOVERY":
            dr = DecisionResult.BLOCK
        else:
            dr = DecisionResult.ALLOW

        logger.record(
            who="langgraph_agent",
            what=action,
            policy="diagnosis",
            reason=diagnosis.get("reason", ""),
            result=dr,
            customer_id="c1",
            payment_id="p1",
        )

        assert logger.count_total() == 1
        assert logger.records[0].who == "langgraph_agent"
