import json

import pytest
from pydantic import ValidationError

from app.llm.dictionary import Intent, Metric, OperationType, Project
from app.llm.parser import LLMParsedResponse, Operation, build_repair_payload, normalize_llm_payload


def test_llm_parsed_response_accepts_data_query() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "project": "obvodny",
                "metrics": ["fact"],
            },
            "operation": None,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.95,
        },
    )

    assert parsed.intent == Intent.DATA_QUERY
    assert parsed.state_delta.project == Project.OBVODNY
    assert parsed.state_delta.metrics == [Metric.FACT]
    assert parsed.operation is None
    assert parsed.confidence == 0.95


def test_llm_parsed_response_accepts_operation() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "math_on_last_result",
            "state_delta": {},
            "operation": {
                "type": "divide",
                "left": {
                    "source": "last_result",
                    "metric": "fact",
                },
                "right": {
                    "source": "literal",
                    "value": 2,
                },
            },
            "needs_clarification": False,
            "confidence": 0.9,
        },
    )

    assert isinstance(parsed.operation, Operation)
    assert parsed.operation.type == OperationType.DIVIDE
    assert parsed.operation.right is not None
    assert parsed.operation.right.value == 2


def test_llm_parsed_response_accepts_dimension_query() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "dimension_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "project": "obvodny",
                "dimension": "article",
                "filters": {"article_kind": "detail"},
            },
            "operation": None,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.91,
        },
    )

    assert parsed.intent == Intent.DIMENSION_QUERY
    assert parsed.state_delta.dimension == "article"


def test_llm_parsed_response_accepts_period_mode_all() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "period": {"mode": "all"},
            },
            "operation": None,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.91,
        },
    )

    assert parsed.state_delta.period is not None
    assert parsed.state_delta.period.mode == "all"


def test_llm_parsed_response_accepts_payment_calendar_view() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "view": "summary",
                "metrics": ["plan", "fact", "deviation"],
            },
            "operation": None,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.9,
        },
    )

    assert parsed.state_delta.view == "summary"


def test_normalize_llm_payload_infers_data_query_intent() -> None:
    payload = normalize_llm_payload(
        {
            "state_delta": {
                "report_type": "payment_calendar",
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    parsed = LLMParsedResponse.model_validate(payload)

    assert parsed.intent == Intent.DATA_QUERY


def test_normalize_llm_payload_infers_dimension_query_intent() -> None:
    payload = normalize_llm_payload(
        {
            "state_delta": {
                "report_type": "payment_calendar",
                "dimension": "article",
            },
            "confidence": 0.9,
        },
    )

    parsed = LLMParsedResponse.model_validate(payload)

    assert parsed.intent == Intent.DIMENSION_QUERY


def test_normalize_llm_payload_maps_generate_report_intent() -> None:
    payload = normalize_llm_payload(
        {
            "intent": "generate_report",
            "state_delta": {
                "report_type": "payment_calendar",
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    parsed = LLMParsedResponse.model_validate(payload)

    assert parsed.intent == Intent.DATA_QUERY


def test_normalize_llm_payload_keeps_empty_payload_invalid() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(normalize_llm_payload({"state_delta": {}}))


def test_normalize_llm_payload_removes_all_mode_from_concrete_period() -> None:
    payload = normalize_llm_payload(
        {
            "intent": "data_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "metrics": ["fact"],
                "period": {
                    "mode": "all",
                    "label": "май",
                },
            },
            "confidence": 0.9,
        },
    )

    assert payload["state_delta"]["period"] == {"label": "май"}


def test_build_repair_payload_contains_validation_context() -> None:
    invalid_payload = {
        "intent": "data_query",
        "state_delta": {"metrics": ["fake_metric"]},
        "confidence": 0.9,
    }
    with pytest.raises(ValidationError) as error:
        LLMParsedResponse.model_validate(invalid_payload)

    payload = json.loads(build_repair_payload(invalid_payload, error.value))

    assert payload["invalid_json"]["state_delta"]["metrics"] == ["fake_metric"]
    assert payload["validation_errors"][0]["loc"] == ["state_delta", "metrics", 0]
    assert payload["schema_shape"]["intent"] == "required enum"


def test_llm_parsed_response_rejects_unknown_intent() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "calculate_everything",
                "state_delta": {"metrics": ["fact"]},
                "confidence": 0.9,
            },
        )


def test_llm_parsed_response_rejects_unknown_metric() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["fake_metric"]},
                "confidence": 0.9,
            },
        )


def test_llm_parsed_response_rejects_unknown_project() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"project": "unknown", "metrics": ["fact"]},
                "confidence": 0.9,
            },
        )


def test_llm_parsed_response_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["fact"]},
                "confidence": 2,
            },
        )


def test_llm_parsed_response_requires_clarification_question() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["fact"]},
                "needs_clarification": True,
                "confidence": 0.7,
            },
        )


def test_llm_parsed_response_requires_operation_for_math() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "math_on_last_result",
                "state_delta": {},
                "confidence": 0.9,
            },
        )


def test_llm_parsed_response_rejects_unknown_extra_field() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["fact"]},
                "confidence": 0.9,
                "sql": "select * from users",
            },
        )
