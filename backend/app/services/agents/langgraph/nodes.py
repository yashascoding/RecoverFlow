from __future__ import annotations

import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.services.agents.langgraph.state import RecoveryState, Stage
from app.services.recovery.failure_diagnosis import FailureDiagnosisEngine
from app.schemas.agent_diagnosis import parse_diagnosis_output, DiagnosisValidationError

logger = get_logger(__name__)

# ── Helper ──────────────────────────────────────────────────────────────────

def _safe_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        uuid.UUID(value)
        return value
    except (ValueError, AttributeError):
        return None


# ── OBSERVE ─────────────────────────────────────────────────────────────────

async def observe_node(state: RecoveryState) -> dict:
    """Fetch customer + payment data using built-in tools."""
    start = time.monotonic()
    new_tool_calls: list[dict] = []

    customer_data: dict[str, Any] = {}
    payment_data: dict[str, Any] = {}
    tools = state.get("_tools") or {}

    # fetch_customer
    fetch_customer = tools.get("fetch_customer")
    if fetch_customer and (state.get("customer_id") or state.get("email")):
        tc_start = time.monotonic()
        try:
            result = await fetch_customer.execute(
                customer_id=state.get("customer_id"),
                email=state.get("email"),
            )
            customer_data = result
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "fetch_customer", "arguments": {"customer_id": state.get("customer_id")}, "result": result, "latency_ms": round(tc_lat, 2)})
        except Exception as e:
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "fetch_customer", "arguments": {"customer_id": state.get("customer_id")}, "error": str(e), "latency_ms": round(tc_lat, 2)})
            logger.warning("observe_fetch_customer_failed", extra={"error": str(e)})

    # fetch_payment
    fetch_payment = tools.get("fetch_payment")
    if fetch_payment and (state.get("payment_id") or state.get("order_id")):
        tc_start = time.monotonic()
        try:
            result = await fetch_payment.execute(
                payment_id=state.get("payment_id"),
                order_id=state.get("order_id"),
            )
            payment_data = result
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "fetch_payment", "arguments": {"payment_id": state.get("payment_id")}, "result": result, "latency_ms": round(tc_lat, 2)})
        except Exception as e:
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "fetch_payment", "arguments": {"payment_id": state.get("payment_id")}, "error": str(e), "latency_ms": round(tc_lat, 2)})
            logger.warning("observe_fetch_payment_failed", extra={"error": str(e)})

    latency = (time.monotonic() - start) * 1000
    latencies = dict(state.get("stage_latencies_ms") or {})
    latencies["observe"] = round(latency, 2)

    return {
        "stage": Stage.INVESTIGATE,
        "customer_data": customer_data,
        "payment_data": payment_data,
        "tool_calls": new_tool_calls,
        "stage_latencies_ms": latencies,
    }


# ── INVESTIGATE ─────────────────────────────────────────────────────────────

async def investigate_node(state: RecoveryState) -> dict:
    """Check consent and diagnose failure reason."""
    start = time.monotonic()
    new_tool_calls: list[dict] = []

    consent_data: dict[str, Any] = {}
    failure_diagnosis: dict[str, Any] = {}
    tools = state.get("_tools") or {}
    customer = state.get("customer_data") or {}
    payment = state.get("payment_data") or {}

    # check_consent
    check_consent = tools.get("check_consent")
    if check_consent and customer.get("id"):
        tc_start = time.monotonic()
        try:
            result = await check_consent.execute(customer_id=customer["id"], channel="email")
            consent_data = result
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "check_consent", "arguments": {"customer_id": customer["id"]}, "result": result, "latency_ms": round(tc_lat, 2)})
        except Exception as e:
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "check_consent", "arguments": {"customer_id": customer["id"]}, "error": str(e), "latency_ms": round(tc_lat, 2)})

    # diagnose_failure (deterministic, no DB needed)
    diagnose_failure = tools.get("diagnose_failure")
    if diagnose_failure and payment.get("failure_reason"):
        tc_start = time.monotonic()
        try:
            result = await diagnose_failure.execute(failure_reason=payment["failure_reason"])
            failure_diagnosis = result
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "diagnose_failure", "arguments": {"failure_reason": payment["failure_reason"]}, "result": result, "latency_ms": round(tc_lat, 2)})
        except Exception as e:
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({"tool_name": "diagnose_failure", "arguments": {"failure_reason": payment["failure_reason"]}, "error": str(e), "latency_ms": round(tc_lat, 2)})

    latency = (time.monotonic() - start) * 1000
    latencies = dict(state.get("stage_latencies_ms") or {})
    latencies["investigate"] = round(latency, 2)

    return {
        "stage": Stage.DIAGNOSE,
        "consent_data": consent_data,
        "failure_diagnosis": failure_diagnosis,
        "tool_calls": new_tool_calls,
        "stage_latencies_ms": latencies,
    }


# ── DIAGNOSE ────────────────────────────────────────────────────────────────

async def diagnose_node(state: RecoveryState) -> dict:
    """Call LLM for structured diagnosis. Falls back to deterministic on error."""
    start = time.monotonic()
    new_tool_calls: list[dict] = []

    llm_call = state.get("_llm_call")

    # Build prompt
    parts = ["You are a payment recovery agent. Diagnose the payment failure and recommend an action.\n"]
    if state.get("customer_data"):
        parts.append(f"Customer: {state['customer_data']}")
    if state.get("payment_data"):
        parts.append(f"Payment: {state['payment_data']}")
    if state.get("consent_data"):
        parts.append(f"Consent: {state['consent_data']}")
    if state.get("failure_diagnosis"):
        parts.append(f"Failure diagnosis: {state['failure_diagnosis']}")
    parts.append(
        '\nRespond with JSON: {"diagnosis": "...", "confidence": 0.0-1.0, '
        '"recommended_action": "...", "reason": "...", '
        '"risk_level": "LOW|MEDIUM|HIGH"}'
    )
    prompt = "\n".join(parts)

    diagnosis_raw: dict[str, Any] = {}
    diagnosis: dict[str, Any] = {}
    error_msg: str | None = None

    if llm_call:
        tc_start = time.monotonic()
        try:
            raw = await llm_call(prompt)
            tc_lat = (time.monotonic() - tc_start) * 1000
            diagnosis_raw = raw if isinstance(raw, dict) else {}
            new_tool_calls.append({
                "tool_name": "llm_call",
                "arguments": {"prompt_length": len(prompt)},
                "result": {"raw_length": len(str(raw))},
                "latency_ms": round(tc_lat, 2),
            })

            parsed = parse_diagnosis_output(diagnosis_raw)
            diagnosis = parsed.model_dump()
        except Exception as e:
            tc_lat = (time.monotonic() - tc_start) * 1000
            new_tool_calls.append({
                "tool_name": "llm_call",
                "arguments": {"prompt_length": len(prompt)},
                "error": str(e),
                "latency_ms": round(tc_lat, 2),
            })
            # Fall through to deterministic fallback below
            llm_call = None

    if not diagnosis:
        # Deterministic fallback — used when no LLM or LLM failed
        failure_diag = state.get("failure_diagnosis") or {}
        category = failure_diag.get("category", "unknown")
        strategy = failure_diag.get("strategy", "alternate_channel")

        action_map = {
            "instant_retry": "RETRY_PAYMENT",
            "delayed_retry": "DELAYED_RETRY",
            "alternate_channel": "SEND_SMS",
            "escalate_to_human": "ESCALATE_TO_HUMAN",
            "block_recovery": "BLOCK_RECOVERY",
        }
        risk_map = {
            "upi_timeout": "LOW",
            "bank_declined": "MEDIUM",
            "network_error": "LOW",
            "gateway_error": "MEDIUM",
            "fraud_check": "HIGH",
            "unknown": "MEDIUM",
        }

        diagnosis = {
            "diagnosis": f"Deterministic diagnosis: {category}",
            "confidence": 0.7,
            "recommended_action": action_map.get(strategy, "EMAIL_PAYMENT_LINK"),
            "reason": failure_diag.get("reason", "Fallback diagnosis"),
            "risk_level": risk_map.get(category, "MEDIUM"),
        }

    latency = (time.monotonic() - start) * 1000
    latencies = dict(state.get("stage_latencies_ms") or {})
    latencies["diagnose"] = round(latency, 2)

    return {
        "stage": Stage.PLAN,
        "llm_diagnosis": diagnosis,
        "diagnosis_raw": diagnosis_raw,
        "tool_calls": new_tool_calls,
        "stage_latencies_ms": latencies,
    }


# ── PLAN ────────────────────────────────────────────────────────────────────

async def plan_node(state: RecoveryState) -> dict:
    """Map diagnosis to concrete recovery actions."""
    start = time.monotonic()

    diagnosis = state.get("llm_diagnosis") or {}
    action = diagnosis.get("recommended_action", "")
    risk = diagnosis.get("risk_level", "HIGH")

    actions: list[dict[str, Any]] = []

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
    else:
        actions.append({"type": "send_email", "template": "payment_link"})

    if risk == "HIGH":
        actions.append({"type": "flag_for_review"})

    latency = (time.monotonic() - start) * 1000
    latencies = dict(state.get("stage_latencies_ms") or {})
    latencies["plan"] = round(latency, 2)

    total_latency = sum(latencies.values())

    return {
        "stage": Stage.COMPLETED,
        "planned_actions": actions,
        "stage_latencies_ms": latencies,
        "total_latency_ms": round(total_latency, 2),
        "tool_calls": [],
    }


# ── Error handler node ──────────────────────────────────────────────────────

async def error_node(state: RecoveryState) -> dict:
    """Terminal error state — captures failure reason."""
    return {
        "stage": Stage.FAILED,
        "error": state.get("error", "Unknown error"),
        "tool_calls": [],
    }


# ── Router ──────────────────────────────────────────────────────────────────

def stage_router(state: RecoveryState) -> str:
    """Decide next node based on current stage.  Returns node name."""
    stage = state.get("stage")

    match stage:
        case Stage.OBSERVE:
            return "observe"
        case Stage.INVESTIGATE:
            return "investigate"
        case Stage.DIAGNOSE:
            return "diagnose"
        case Stage.PLAN:
            return "plan"
        case Stage.FAILED:
            return "__end__"
        case Stage.COMPLETED:
            return "__end__"
        case _:
            return "error"
