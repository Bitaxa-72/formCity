from app.context_resolver import empty_dialog_state, normalize_state, resolve_context
from app.llm_parser import LLMParsedResponse


def test_empty_dialog_state_shape() -> None:
    state = empty_dialog_state()

    assert state["report_type"] is None
    assert state["period"] == {"from": None, "to": None, "label": None}
    assert state["metrics"] == []
    assert state["awaiting_clarification"] is False


def test_normalize_state_merges_known_values_with_defaults() -> None:
    state = normalize_state({"project": "obvodny_118", "period": {"from": "2026-03-01"}})

    assert state["project"] == "obvodny_118"
    assert state["period"]["from"] == "2026-03-01"
    assert state["period"]["to"] is None
    assert state["metrics"] == []


def test_resolve_context_data_query_starts_new_state() -> None:
    current_state = {
        "project": "well_moskovsky",
        "metrics": ["debt"],
        "group_by": ["floor"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "project": "obvodny_118",
                "metrics": ["revenue"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny_118"
    assert resolved["metrics"] == ["revenue"]
    assert resolved["group_by"] == []
    assert resolved["last_intent"] == "data_query"


def test_resolve_context_context_query_keeps_previous_state() -> None:
    current_state = {
        "project": "obvodny_118",
        "period": {"from": "2026-03-01", "to": "2026-03-31"},
        "metrics": ["revenue"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "group_by": ["floor"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny_118"
    assert resolved["period"]["from"] == "2026-03-01"
    assert resolved["metrics"] == ["revenue"]
    assert resolved["group_by"] == ["floor"]
    assert resolved["last_intent"] == "context_query"


def test_resolve_context_clarification_answer_applies_delta() -> None:
    current_state = {
        "metrics": ["revenue"],
        "awaiting_clarification": True,
        "clarification_target": "Уточните проект.",
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "clarification_answer",
            "state_delta": {
                "project": "obvodny_118",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny_118"
    assert resolved["metrics"] == ["revenue"]
    assert resolved["awaiting_clarification"] is False
    assert resolved["clarification_target"] is None


def test_resolve_context_sets_clarification_state() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "metrics": ["revenue"],
            },
            "needs_clarification": True,
            "clarification_question": "Уточните проект.",
            "confidence": 0.7,
        },
    )

    resolved = resolve_context({}, parsed)

    assert resolved["awaiting_clarification"] is True
    assert resolved["clarification_target"] == "Уточните проект."


def test_resolve_context_math_keeps_state_and_sets_pending_operation() -> None:
    current_state = {
        "project": "obvodny_118",
        "metrics": ["revenue"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "math_on_last_result",
            "state_delta": {},
            "operation": {
                "type": "divide",
                "left": {"source": "last_result", "metric": "revenue"},
                "right": {"source": "literal", "value": 2},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny_118"
    assert resolved["metrics"] == ["revenue"]
    assert resolved["pending_operation"]["type"] == "divide"


def test_resolve_context_general_question_keeps_state() -> None:
    current_state = {
        "project": "obvodny_118",
        "metrics": ["revenue"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "general_question",
            "state_delta": {},
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny_118"
    assert resolved["metrics"] == ["revenue"]
    assert resolved["last_intent"] == "general_question"
