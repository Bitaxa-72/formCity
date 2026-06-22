import pytest
from pydantic import ValidationError

from app.llm_dictionary import Intent, Metric, OperationType, Project
from app.llm_parser import LLMParsedResponse, Operation


def test_llm_parsed_response_accepts_data_query() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "project": "obvodny_118",
                "metrics": ["revenue"],
            },
            "operation": None,
            "needs_clarification": False,
            "clarification_question": None,
            "confidence": 0.95,
        },
    )

    assert parsed.intent == Intent.DATA_QUERY
    assert parsed.state_delta.project == Project.OBVODNY_118
    assert parsed.state_delta.metrics == [Metric.REVENUE]
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
                    "metric": "revenue",
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


def test_llm_parsed_response_requires_intent() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate({"state_delta": {}})


def test_llm_parsed_response_rejects_unknown_intent() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "calculate_everything",
                "state_delta": {"metrics": ["revenue"]},
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


def test_llm_parsed_response_rejects_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["revenue"]},
                "confidence": 2,
            },
        )


def test_llm_parsed_response_requires_clarification_question() -> None:
    with pytest.raises(ValidationError):
        LLMParsedResponse.model_validate(
            {
                "intent": "data_query",
                "state_delta": {"metrics": ["revenue"]},
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
                "state_delta": {"metrics": ["revenue"]},
                "confidence": 0.9,
                "sql": "select * from users",
            },
        )
