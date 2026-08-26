from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.schemas.agent_diagnosis import (
    AgentDiagnosisOutput,
    DiagnosisValidationError,
    parse_diagnosis_output,
)
from app.services.agents.agent_trace import AgentTrace, StageTrace, ToolCall
from app.services.agents.state_machine import (
    AgentState,
    AgentStateMachine,
    InvalidStateTransitionError,
)
from app.services.consent.consent_service import ConsentService
from app.services.recovery.failure_diagnosis import FailureDiagnosisEngine
from app.services.recovery.recovery_service_v2 import (
    CustomerNotFoundError,
    InvalidPaymentStateError,
    PaymentNotFoundError,
    RecoveryServiceV2,
)

logger = get_logger(__name__)

# ── Exceptions ──────────────────────────────────────────────────────────────

class AgentError(Exception):
    """Base exception for agent failures."""


class LLMTimeoutError(AgentError):
    def __init__(self, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds
        super().__init__(f"LLM call timed out after {timeout_seconds}s")


class LLMResponseError(AgentError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"LLM response error: {reason}")


class ToolTimeoutError(AgentError):
    def __init__(self, tool_name: str, timeout_seconds: float) -> None:
        self.tool_name = tool_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Tool '{tool_name}' timed out after {timeout_seconds}s")


# ── Tool protocol ───────────────────────────────────────────────────────────

@runtime_checkable
class AgentTool(Protocol):
    name: str

    async def execute(self, **kwargs: Any) -> dict: ...


# ── Built-in tools ──────────────────────────────────────────────────────────

class FetchCustomerTool:
    name = "fetch_customer"

    def __init__(self, svc: RecoveryServiceV2) -> None:
        self._svc = svc

    async def execute(self, customer_id: str | None = None, email: str | None = None, **_: Any) -> dict:
        if email:
            c = await self._svc.get_customer_by_email(email)
        elif customer_id:
            c = await self._svc.get_customer(uuid.UUID(customer_id))
        else:
            raise ValueError("customer_id or email required")
        return {"id": str(c.id), "email": c.email, "name": c.name, "status": c.status}


class FetchPaymentTool:
    name = "fetch_payment"

    def __init__(self, svc: RecoveryServiceV2) -> None:
        self._svc = svc

    async def execute(self, payment_id: str | None = None, order_id: str | None = None, **_: Any) -> dict:
        if order_id:
            p = await self._svc.get_payment_by_order(order_id)
        elif payment_id:
            p = await self._svc.get_payment(uuid.UUID(payment_id))
        else:
            raise ValueError("payment_id or order_id required")
        return {
            "id": str(p.id),
            "order_id": p.razorpay_order_id,
            "amount": p.amount,
            "status": p.status,
            "failure_reason": p.failure_reason,
            "customer_email": p.customer_email,
            "customer_id": str(p.customer_id) if p.customer_id else None,
        }


class CheckConsentTool:
    name = "check_consent"

    def __init__(self, svc: ConsentService) -> None:
        self._svc = svc

    async def execute(self, customer_id: str, channel: str = "email", **_: Any) -> dict:
        has = await self._svc.validate_consent(uuid.UUID(customer_id), channel)
        return {"has_consent": has, "channel": channel}


class DiagnoseFailureTool:
    name = "diagnose_failure"

    def __init__(self) -> None:
        self._engine = FailureDiagnosisEngine()

    async def execute(self, failure_reason: str | None = None, **_: Any) -> dict:
        result = self._engine.diagnose(failure_reason)
        return result.to_dict()


# ── RecoveryAgent ───────────────────────────────────────────────────────────

class RecoveryAgent:
    """Orchestrates the 4-stage recovery workflow:
    OBSERVE → INVESTIGATE → DIAGNOSE → PLAN
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        llm_call: Any = None,
        llm_timeout: float = 30.0,
        tool_timeout: float = 10.0,
        tools: list[AgentTool] | None = None,
    ) -> None:
        self.db = db
        self._llm_call = llm_call or self._default_llm_call
        self._llm_timeout = llm_timeout
        self._tool_timeout = tool_timeout

        self.recovery_svc = RecoveryServiceV2(db)
        self.consent_svc = ConsentService(db)

        default_tools: list[AgentTool] = [
            FetchCustomerTool(self.recovery_svc),
            FetchPaymentTool(self.recovery_svc),
            CheckConsentTool(self.consent_svc),
            DiagnoseFailureTool(),
        ]
        self._tools: dict[str, AgentTool] = {
            t.name: t for t in (tools or default_tools)
        }

    # ── tool execution ───────────────────────────────────────────────────

    async def _run_tool(self, name: str, trace: AgentTrace, state: AgentState, **kwargs: Any) -> dict:
        tool = self._tools.get(name)
        if not tool:
            raise AgentError(f"Unknown tool: {name}")

        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                tool.execute(**kwargs),
                timeout=self._tool_timeout,
            )
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name=name,
                arguments=kwargs,
                result=result,
                latency_ms=latency,
            )
            return result
        except asyncio.TimeoutError:
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name=name,
                arguments=kwargs,
                error="timeout",
                latency_ms=latency,
            )
            raise ToolTimeoutError(name, self._tool_timeout)
        except (CustomerNotFoundError, PaymentNotFoundError, InvalidPaymentStateError, ValueError) as e:
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name=name,
                arguments=kwargs,
                error=str(e),
                latency_ms=latency,
            )
            raise
        except AgentError:
            raise
        except Exception as e:
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name=name,
                arguments=kwargs,
                error=str(e),
                latency_ms=latency,
            )
            raise AgentError(f"Tool '{name}' failed: {e}") from e

    # ── LLM call ─────────────────────────────────────────────────────────

    async def _call_llm(self, prompt: str, trace: AgentTrace, state: AgentState) -> dict:
        start = time.monotonic()
        try:
            raw = await asyncio.wait_for(
                self._llm_call(prompt),
                timeout=self._llm_timeout,
            )
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name="llm_call",
                arguments={"prompt_length": len(prompt)},
                result={"raw_length": len(str(raw)) if raw else 0},
                latency_ms=latency,
            )
            return raw if isinstance(raw, dict) else {}
        except asyncio.TimeoutError:
            latency = (time.monotonic() - start) * 1000
            trace.record_tool_call(
                state=state,
                tool_name="llm_call",
                arguments={"prompt_length": len(prompt)},
                error="timeout",
                latency_ms=latency,
            )
            raise LLMTimeoutError(self._llm_timeout)

    # ── stages ───────────────────────────────────────────────────────────

    async def _observe(self, context: dict, trace: AgentTrace) -> StageTrace:
        stage = trace.begin_stage(AgentState.OBSERVE, input_data=context)

        customer_data = None
        payment_data = None

        if context.get("customer_id") or context.get("email"):
            customer_data = await self._run_tool(
                "fetch_customer", trace, AgentState.OBSERVE,
                customer_id=context.get("customer_id"),
                email=context.get("email"),
            )

        if context.get("payment_id") or context.get("order_id"):
            payment_data = await self._run_tool(
                "fetch_payment", trace, AgentState.OBSERVE,
                payment_id=context.get("payment_id"),
                order_id=context.get("order_id"),
            )

        output = {"customer": customer_data, "payment": payment_data}
        trace.complete_stage(AgentState.OBSERVE, output=output)
        return stage

    async def _investigate(self, observe_output: dict, trace: AgentTrace) -> StageTrace:
        stage = trace.begin_stage(AgentState.INVESTIGATE, input_data=observe_output)

        customer = observe_output.get("customer")
        payment = observe_output.get("payment")
        consent_data = None
        diagnosis_data = None

        if customer and customer.get("id"):
            consent_data = await self._run_tool(
                "check_consent", trace, AgentState.INVESTIGATE,
                customer_id=customer["id"],
                channel="email",
            )

        if payment and payment.get("failure_reason"):
            diagnosis_data = await self._run_tool(
                "diagnose_failure", trace, AgentState.INVESTIGATE,
                failure_reason=payment["failure_reason"],
            )

        output = {
            "consent": consent_data,
            "failure_diagnosis": diagnosis_data,
            "payment_status": payment.get("status") if payment else None,
        }
        trace.complete_stage(AgentState.INVESTIGATE, output=output)
        return stage

    async def _diagnose(self, full_context: dict, trace: AgentTrace) -> StageTrace:
        stage = trace.begin_stage(AgentState.DIAGNOSE, input_data=full_context)

        prompt = self._build_diagnosis_prompt(full_context)
        raw_llm = await self._call_llm(prompt, trace, AgentState.DIAGNOSE)

        try:
            diagnosis = parse_diagnosis_output(raw_llm)
            output = diagnosis.model_dump()
            trace.complete_stage(AgentState.DIAGNOSE, output=output)
        except DiagnosisValidationError as e:
            trace.complete_stage(
                AgentState.DIAGNOSE,
                error=f"Malformed LLM output: {e}",
                output={"raw": raw_llm, "errors": e.errors},
            )
            raise LLMResponseError(f"Malformed diagnosis: {e}") from e

        return stage

    async def _plan(self, diagnosis: dict, trace: AgentTrace) -> StageTrace:
        stage = trace.begin_stage(AgentState.PLAN, input_data=diagnosis)

        actions = self._determine_actions(diagnosis)
        output = {"recommended_actions": actions, "diagnosis_summary": diagnosis}
        trace.complete_stage(AgentState.PLAN, output=output)
        return stage

    # ── prompt + action planning ─────────────────────────────────────────

    def _build_diagnosis_prompt(self, context: dict) -> str:
        parts = ["You are a payment recovery agent. Diagnose the payment failure and recommend an action.\n"]
        if context.get("customer"):
            parts.append(f"Customer: {context['customer']}")
        if context.get("payment"):
            parts.append(f"Payment: {context['payment']}")
        if context.get("consent"):
            parts.append(f"Consent: {context['consent']}")
        if context.get("failure_diagnosis"):
            parts.append(f"Failure diagnosis: {context['failure_diagnosis']}")
        parts.append("\nRespond with JSON: {\"diagnosis\": \"...\", \"confidence\": 0.0-1.0, \"recommended_action\": \"...\", \"reason\": \"...\", \"risk_level\": \"LOW|MEDIUM|HIGH\"}")
        return "\n".join(parts)

    def _determine_actions(self, diagnosis: dict) -> list[dict]:
        action = diagnosis.get("recommended_action", "")
        risk = diagnosis.get("risk_level", "HIGH")
        actions = []

        if action == "EMAIL_PAYMENT_LINK":
            actions.append({"type": "send_email", "template": "payment_link"})
        elif action == "RETRY_PAYMENT":
            actions.append({"type": "retry_payment", "delay_seconds": 0})
        elif action == "DELAYED_RETRY":
            actions.append({"type": "retry_payment", "delay_seconds": 3600})
        elif action == "SEND_SMS":
            actions.append({"type": "send_sms"})
        elif action == "SEND_WHATSAPP":
            actions.append({"type": "send_whatsapp"})
        elif action == "ESCALATE_TO_HUMAN":
            actions.append({"type": "escalate", "reason": diagnosis.get("reason", "")})
        elif action == "BLOCK_RECOVERY":
            actions.append({"type": "block", "reason": diagnosis.get("reason", "")})

        if risk == "HIGH":
            actions.append({"type": "flag_for_review"})

        return actions

    # ── default LLM (stub) ───────────────────────────────────────────────

    async def _default_llm_call(self, prompt: str) -> dict:
        return {
            "diagnosis": "Automated diagnosis based on failure analysis",
            "confidence": 0.5,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "Default recovery action",
            "risk_level": "LOW",
        }

    # ── main entry point ─────────────────────────────────────────────────

    @staticmethod
    def _safe_uuid(value: str | None) -> uuid.UUID | None:
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None

    async def run(self, context: dict) -> dict:
        sm = AgentStateMachine()
        trace = AgentTrace(
            payment_id=self._safe_uuid(context.get("payment_id")),
            customer_id=self._safe_uuid(context.get("customer_id")),
        )

        try:
            # OBSERVE
            await self._observe(context, trace)
            sm.transition(AgentState.INVESTIGATE)

            # INVESTIGATE
            observe_out = trace.stages[0].output_data or {}
            await self._investigate(observe_out, trace)
            sm.transition(AgentState.DIAGNOSE)

            # DIAGNOSE
            investigate_out = trace.stages[1].output_data or {}
            full_context = {**observe_out, **investigate_out}
            await self._diagnose(full_context, trace)
            sm.transition(AgentState.PLAN)

            # PLAN
            diagnose_out = trace.stages[2].output_data or {}
            await self._plan(diagnose_out, trace)
            sm.transition(AgentState.COMPLETED)

            trace.complete(AgentState.COMPLETED)

        except Exception as e:
            current = sm.state
            if sm.can_transition(AgentState.FAILED):
                sm.transition(AgentState.FAILED)
            trace.complete_stage(current, error=str(e))
            trace.complete(AgentState.FAILED)

            logger.error(
                "agent_run_failed",
                extra={"state": current.value, "error": str(e), "run_id": str(trace.run_id)},
            )
            return {
                "success": False,
                "error": str(e),
                "state": sm.state.value,
                "trace": trace.to_dict(),
            }

        return {
            "success": True,
            "state": sm.state.value,
            "trace": trace.to_dict(),
        }
