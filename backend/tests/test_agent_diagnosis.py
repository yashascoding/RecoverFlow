import json

import pytest

from app.schemas.agent_diagnosis import (
    AgentDiagnosisOutput,
    DiagnosisValidationError,
    RecommendedAction,
    RiskLevel,
    parse_diagnosis_output,
)


class TestAgentDiagnosisOutputSchema:
    """Valid inputs should parse cleanly."""

    def test_valid_full_output(self):
        data = {
            "diagnosis": "Payment failed due to UPI timeout",
            "confidence": 0.91,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "UPI timeout is usually transient",
            "risk_level": "LOW",
        }
        result = AgentDiagnosisOutput.model_validate(data)
        assert result.diagnosis == "Payment failed due to UPI timeout"
        assert result.confidence == 0.91
        assert result.recommended_action == RecommendedAction.EMAIL_PAYMENT_LINK
        assert result.reason == "UPI timeout is usually transient"
        assert result.risk_level == RiskLevel.LOW

    def test_valid_minimal_boundaries(self):
        data = {
            "diagnosis": "x",
            "confidence": 0.0,
            "recommended_action": "BLOCK_RECOVERY",
            "reason": "y",
            "risk_level": "HIGH",
        }
        result = AgentDiagnosisOutput.model_validate(data)
        assert result.confidence == 0.0

    def test_confidence_one(self):
        data = {
            "diagnosis": "Confirmed fraud",
            "confidence": 1.0,
            "recommended_action": "ESCALATE_TO_HUMAN",
            "reason": "Fraud detected",
            "risk_level": "HIGH",
        }
        result = AgentDiagnosisOutput.model_validate(data)
        assert result.confidence == 1.0

    def test_all_actions_valid(self):
        for action in RecommendedAction:
            data = {
                "diagnosis": "test",
                "confidence": 0.5,
                "recommended_action": action.value,
                "reason": "test",
                "risk_level": "LOW",
            }
            result = AgentDiagnosisOutput.model_validate(data)
            assert result.recommended_action == action

    def test_all_risk_levels_valid(self):
        for level in RiskLevel:
            data = {
                "diagnosis": "test",
                "confidence": 0.5,
                "recommended_action": "EMAIL_PAYMENT_LINK",
                "reason": "test",
                "risk_level": level.value,
            }
            result = AgentDiagnosisOutput.model_validate(data)
            assert result.risk_level == level

    def test_whitespace_stripped(self):
        data = {
            "diagnosis": "  some diagnosis  ",
            "confidence": 0.75,
            "recommended_action": "RETRY_PAYMENT",
            "reason": "  some reason  ",
            "risk_level": "MEDIUM",
        }
        result = AgentDiagnosisOutput.model_validate(data)
        assert result.diagnosis == "some diagnosis"
        assert result.reason == "some reason"


class TestRejectsMalformed:
    """Malformed inputs must be rejected with clear errors."""

    def test_empty_string(self):
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output("not json at all")
        assert "Invalid JSON" in str(exc_info.value)

    def test_not_json(self):
        with pytest.raises(DiagnosisValidationError):
            parse_diagnosis_output("{{{{")

    def test_not_object(self):
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output('["diagnosis", "reason"]')
        assert "Expected object" in str(exc_info.value)

    def test_list_input(self):
        with pytest.raises(DiagnosisValidationError):
            parse_diagnosis_output([1, 2, 3])

    def test_missing_diagnosis(self):
        data = {
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_missing_confidence(self):
        data = {
            "diagnosis": "test",
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_missing_recommended_action(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_missing_reason(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_missing_risk_level(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_empty_object(self):
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output({})
        assert len(exc_info.value.errors) >= 4

    def test_confidence_below_zero(self):
        data = {
            "diagnosis": "test",
            "confidence": -0.1,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_confidence_above_one(self):
        data = {
            "diagnosis": "test",
            "confidence": 1.5,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_invalid_action(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "recommended_action": "DO_SOMETHING_RANDOM",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_invalid_risk_level(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "CRITICAL",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_empty_diagnosis(self):
        data = {
            "diagnosis": "",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_empty_reason(self):
        data = {
            "diagnosis": "test",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_null_values(self):
        data = {
            "diagnosis": None,
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "test",
            "risk_level": "LOW",
        }
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert exc_info.value.errors

    def test_extra_fields_ignored(self):
        data = {
            "diagnosis": "UPI timeout",
            "confidence": 0.9,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "transient error",
            "risk_level": "LOW",
            "unexpected_field": "should be ignored",
        }
        result = AgentDiagnosisOutput.model_validate(data)
        assert result.diagnosis == "UPI timeout"


class TestParseFromJsonString:
    """Test parsing from raw JSON strings (LLM output)."""

    def test_valid_json_string(self):
        raw = json.dumps({
            "diagnosis": "Bank declined the card",
            "confidence": 0.85,
            "recommended_action": "DELAYED_RETRY",
            "reason": "Bank declines are often temporary",
            "risk_level": "MEDIUM",
        })
        result = parse_diagnosis_output(raw)
        assert result.recommended_action == RecommendedAction.DELAYED_RETRY
        assert result.risk_level == RiskLevel.MEDIUM

    def test_json_with_markdown_fences(self):
        raw = '```json\n' + json.dumps({
            "diagnosis": "Gateway error",
            "confidence": 0.7,
            "recommended_action": "RETRY_PAYMENT",
            "reason": "502 error",
            "risk_level": "LOW",
        }) + '\n```'
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(raw)
        assert "Invalid JSON" in str(exc_info.value)

    def test_json_with_extra_text(self):
        raw = 'Here is the result:\n' + json.dumps({
            "diagnosis": "Fraud detected",
            "confidence": 0.95,
            "recommended_action": "ESCALATE_TO_HUMAN",
            "reason": "Suspicious pattern",
            "risk_level": "HIGH",
        })
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(raw)
        assert "Invalid JSON" in str(exc_info.value)

    def test_valid_dict_input(self):
        raw = {
            "diagnosis": "UPI timeout",
            "confidence": 0.8,
            "recommended_action": "EMAIL_PAYMENT_LINK",
            "reason": "Transient",
            "risk_level": "LOW",
        }
        result = parse_diagnosis_output(raw)
        assert result.diagnosis == "UPI timeout"


class TestErrorDetails:
    """Ensure error details are captured for debugging."""

    def test_raw_output_preserved(self):
        raw = "garbage input"
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(raw)
        assert exc_info.value.raw_output == raw

    def test_errors_contain_location(self):
        data = {"diagnosis": "test"}  # missing 4 fields
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        locations = [e["loc"] for e in exc_info.value.errors]
        assert len(locations) >= 4

    def test_error_count(self):
        data = {}
        with pytest.raises(DiagnosisValidationError) as exc_info:
            parse_diagnosis_output(data)
        assert len(exc_info.value.errors) >= 5
