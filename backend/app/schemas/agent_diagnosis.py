from __future__ import annotations

import json
import logging
from enum import Enum

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class RecommendedAction(str, Enum):
    EMAIL_PAYMENT_LINK = "EMAIL_PAYMENT_LINK"
    RETRY_PAYMENT = "RETRY_PAYMENT"
    SEND_SMS = "SEND_SMS"
    SEND_WHATSAPP = "SEND_WHATSAPP"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    BLOCK_RECOVERY = "BLOCK_RECOVERY"
    DELAYED_RETRY = "DELAYED_RETRY"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AgentDiagnosisOutput(BaseModel):
    """Structured output schema for the recovery agent's LLM diagnosis."""

    diagnosis: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Human-readable diagnosis of the payment failure",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0",
    )
    recommended_action: RecommendedAction = Field(
        ...,
        description="The recommended recovery action",
    )
    reason: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Reason for the recommended action",
    )
    risk_level: RiskLevel = Field(
        ...,
        description="Risk assessment level",
    )

    @field_validator("diagnosis", "reason")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class DiagnosisValidationError(Exception):
    """Raised when LLM output fails schema validation."""

    def __init__(self, errors: list[dict], raw_output: str) -> None:
        self.errors = errors
        self.raw_output = raw_output
        summary = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in errors[:5]
        )
        super().__init__(f"Diagnosis validation failed: {summary}")


def parse_diagnosis_output(raw: str | dict) -> AgentDiagnosisOutput:
    """Parse and validate raw LLM output into a structured diagnosis.

    Accepts a JSON string or a pre-parsed dict.
    Raises DiagnosisValidationError on malformed or invalid output.
    """
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning("diagnosis_json_decode_error", extra={"error": str(e)})
            raise DiagnosisValidationError(
                errors=[{"loc": ["root"], "msg": f"Invalid JSON: {e}"}],
                raw_output=raw,
            ) from e
    else:
        parsed = raw

    if not isinstance(parsed, dict):
        raise DiagnosisValidationError(
            errors=[{"loc": ["root"], "msg": f"Expected object, got {type(parsed).__name__}"}],
            raw_output=str(raw),
        )

    try:
        return AgentDiagnosisOutput.model_validate(parsed)
    except Exception as e:
        errors = e.errors() if hasattr(e, "errors") else [{"loc": ["root"], "msg": str(e)}]
        logger.warning(
            "diagnosis_validation_failed",
            extra={"error_count": len(errors), "raw_output": str(raw)[:500]},
        )
        raise DiagnosisValidationError(errors=errors, raw_output=str(raw)) from e
