from __future__ import annotations

from typing import Any, Callable, Coroutine

from langgraph.graph import END, StateGraph

from app.core.logging import get_logger
from app.services.agents.langgraph.nodes import (
    diagnose_node,
    error_node,
    investigate_node,
    observe_node,
    plan_node,
    stage_router,
)
from app.services.agents.langgraph.state import RecoveryState, Stage
from app.services.agents.langgraph.trace_store import RunRecord, TraceStore

logger = get_logger(__name__)


class RecoveryGraph:
    """LangGraph-based recovery agent.

    Builds a state machine:
        OBSERVE → INVESTIGATE → DIAGNOSE → PLAN → COMPLETED
        any stage  →  (on error)  →  FAILED

    Usage:
        graph = RecoveryGraph()
        result = await graph.run(
            payment_id="...",
            customer_id="...",
            tools={...},
            llm_call=my_llm_fn,
        )
    """

    def __init__(self) -> None:
        self._graph = self._build_graph()
        self._compiled = self._graph.compile()
        self._trace_store = TraceStore()

    @property
    def trace_store(self) -> TraceStore:
        return self._trace_store

    def _build_graph(self) -> StateGraph:
        g = StateGraph(RecoveryState)

        g.add_node("observe", observe_node)
        g.add_node("investigate", investigate_node)
        g.add_node("diagnose", diagnose_node)
        g.add_node("plan", plan_node)
        g.add_node("error", error_node)

        g.set_entry_point("observe")

        # Conditional routing from each stage
        for node_name in ("observe", "investigate", "diagnose", "plan", "error"):
            g.add_conditional_edges(
                node_name,
                stage_router,
                {
                    "observe": "observe",
                    "investigate": "investigate",
                    "diagnose": "diagnose",
                    "plan": "plan",
                    "error": "error",
                    "__end__": END,
                },
            )

        return g

    async def run(
        self,
        *,
        payment_id: str | None = None,
        customer_id: str | None = None,
        order_id: str | None = None,
        email: str | None = None,
        tools: dict[str, Any] | None = None,
        llm_call: Callable[[str], Coroutine[Any, Any, dict]] | None = None,
    ) -> dict[str, Any]:
        """Execute the full 4-stage recovery pipeline."""
        run_record = self._trace_store.create_run(
            agent_type="recovery",
            payment_id=payment_id,
            customer_id=customer_id,
            input_data={
                "payment_id": payment_id,
                "customer_id": customer_id,
                "order_id": order_id,
                "email": email,
            },
        )

        initial_state: RecoveryState = {
            "run_id": run_record.run_id,
            "payment_id": payment_id or "",
            "customer_id": customer_id or "",
            "stage": Stage.OBSERVE,
            "error": None,
            "customer_data": {},
            "payment_data": {},
            "consent_data": {},
            "failure_diagnosis": {},
            "llm_diagnosis": {},
            "diagnosis_raw": {},
            "planned_actions": [],
            "tool_calls": [],
            "stage_latencies_ms": {},
            "total_latency_ms": 0.0,
            "_llm_call": llm_call,
            "_tools": tools or {},
        }

        try:
            # Run the graph
            final_state = await self._compiled.ainvoke(initial_state)

            # Record stages in trace
            for stage_name in ("observe", "investigate", "diagnose", "plan"):
                stage_input = final_state.get(f"{stage_name}_data") if stage_name in ("observe",) else {}
                stage_output = final_state.get(f"{stage_name}_data") if stage_name in ("observe",) else {}
                self._trace_store.begin_stage(run_record.run_id, stage_name, input_data=stage_input)

                # Collect tool calls for this stage
                all_tool_calls = final_state.get("tool_calls") or []
                for tc in all_tool_calls:
                    if tc.get("tool_name") in self._stage_tool_map.get(stage_name, []):
                        self._trace_store.record_tool_call(
                            run_record.run_id, stage_name,
                            tool_name=tc["tool_name"],
                            arguments=tc.get("arguments"),
                            result=tc.get("result"),
                            error=tc.get("error"),
                            latency_ms=tc.get("latency_ms", 0),
                        )

                self._trace_store.complete_stage(
                    run_record.run_id, stage_name,
                    output=stage_output,
                    error=final_state.get("error"),
                )

            # Record planned actions
            for action in (final_state.get("planned_actions") or []):
                self._trace_store.record_action(
                    run_record.run_id,
                    action_type=action.get("type", "unknown"),
                    payload=action,
                    status="pending",
                )

            final_stage = final_state.get("stage")
            if final_stage == Stage.FAILED:
                run_record.complete(status="failed", error=final_state.get("error"))
            else:
                run_record.complete(status="completed")
                run_record.output_data = {
                    "diagnosis": final_state.get("llm_diagnosis"),
                    "planned_actions": final_state.get("planned_actions"),
                }

            logger.info(
                "recovery_graph_completed",
                extra={
                    "run_id": run_record.run_id,
                    "status": run_record.status,
                    "total_latency_ms": final_state.get("total_latency_ms", 0),
                },
            )

            return {
                "success": final_stage != Stage.FAILED,
                "run_id": run_record.run_id,
                "status": run_record.status,
                "stage": final_state.get("stage", Stage.FAILED).value
                if hasattr(final_state.get("stage", Stage.FAILED), "value")
                else str(final_state.get("stage", "failed")),
                "diagnosis": final_state.get("llm_diagnosis"),
                "planned_actions": final_state.get("planned_actions"),
                "stage_latencies_ms": final_state.get("stage_latencies_ms"),
                "total_latency_ms": final_state.get("total_latency_ms"),
                "trace": run_record.to_dict(),
            }

        except Exception as e:
            run_record.complete(status="failed", error=str(e))
            logger.error(
                "recovery_graph_failed",
                extra={"run_id": run_record.run_id, "error": str(e)},
            )
            return {
                "success": False,
                "run_id": run_record.run_id,
                "status": "failed",
                "error": str(e),
                "trace": run_record.to_dict(),
            }

    # Which tools belong to which stage (for trace attribution)
    _stage_tool_map: dict[str, list[str]] = {
        "observe": ["fetch_customer", "fetch_payment"],
        "investigate": ["check_consent", "diagnose_failure"],
        "diagnose": ["llm_call"],
        "plan": [],
    }
