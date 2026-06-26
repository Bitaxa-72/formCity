from app.llm.parser import LLMParsedResponse
from app.pipeline.context_resolver import empty_dialog_state, normalize_state, resolve_context, set_clarification_state


def test_empty_dialog_state_shape() -> None:
    state = empty_dialog_state()

    assert state["report_type"] is None
    assert state["period"] == {"from": None, "to": None, "label": None}
    assert state["metrics"] == []
    assert state["awaiting_clarification"] is False


def test_normalize_state_merges_known_values_with_defaults() -> None:
    state = normalize_state({"project": "obvodny", "period": {"from": "2026-03-01"}})

    assert state["project"] == "obvodny"
    assert state["period"]["from"] == "2026-03-01"
    assert state["period"]["to"] is None
    assert state["metrics"] == []


def test_resolve_context_data_query_starts_new_state() -> None:
    current_state = {
        "project": "moskovsky",
        "metrics": ["plan"],
        "group_by": ["metric"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "project": "obvodny",
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny"
    assert resolved["metrics"] == ["fact"]
    assert resolved["group_by"] == []
    assert resolved["last_intent"] == "data_query"


def test_resolve_context_partial_data_query_keeps_previous_report_and_period() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": "2026-03-01", "to": "2026-03-31", "label": "march"},
        "metrics": ["plan", "fact", "deviation"],
        "filters": {},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "metrics": ["fact"],
                "filters": {"article": "marketing"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["report_type"] == "payment_calendar"
    assert resolved["period"] == {"from": "2026-03-01", "to": "2026-03-31", "label": "march"}
    assert resolved["metrics"] == ["fact"]
    assert resolved["filters"] == {"article": "marketing"}
    assert resolved["last_intent"] == "data_query"


def test_resolve_context_partial_scope_change_without_metrics_uses_payment_calendar_defaults() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": "2026-03-01", "to": "2026-03-31", "label": "march"},
        "metrics": ["fact"],
        "filters": {"article": "marketing"},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "project": "moskovsky",
                "period": {"label": "may"},
                "filters": {"article": "agent fees"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["report_type"] == "payment_calendar"
    assert resolved["project"] == "moskovsky"
    assert resolved["period"]["label"] == "may"
    assert resolved["filters"] == {"article": "agent fees"}
    assert resolved["metrics"] == ["plan", "fact", "deviation"]


def test_resolve_context_context_query_keeps_previous_state() -> None:
    current_state = {
        "project": "obvodny",
        "period": {"from": "2026-03-01", "to": "2026-03-31"},
        "metrics": ["fact"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "group_by": ["metric"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny"
    assert resolved["period"]["from"] == "2026-03-01"
    assert resolved["metrics"] == ["fact"]
    assert resolved["group_by"] == ["metric"]
    assert resolved["last_intent"] == "context_query"


def test_resolve_context_period_mode_all_clears_period() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "obvodny",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["fact"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "period": {"mode": "all"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["period"] == {"from": None, "to": None, "label": "весь доступный период"}
    assert resolved["metrics"] == ["fact"]


def test_resolve_context_dimension_clears_metrics_and_group_by() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "obvodny",
        "metrics": ["fact"],
        "group_by": ["article"],
        "filters": {"period": "may"},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "dimension": "article",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["dimension"] == "article"
    assert resolved["metrics"] == []
    assert resolved["group_by"] == []
    assert resolved["filters"] == {"period": "may"}


def test_resolve_context_metrics_clear_dimension_but_keep_group_by() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "obvodny",
        "dimension": "article",
        "filters": {"period": "may"},
        "group_by": ["article"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["metrics"] == ["fact"]
    assert resolved["dimension"] is None
    assert resolved["group_by"] == ["article"]
    assert resolved["filters"] == {"period": "may"}


def test_resolve_context_report_type_change_clears_lower_tree() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "obvodny",
        "period": {"from": "2026-05-01", "to": "2026-05-31"},
        "metrics": ["fact"],
        "filters": {"article": "rent"},
        "group_by": ["article"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "report_type": "summary",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["report_type"] == "summary"
    assert resolved["project"] == "obvodny"
    assert resolved["period"] == {"from": None, "to": None, "label": None}
    assert resolved["metrics"] == []
    assert resolved["dimension"] is None
    assert resolved["filters"] == {}
    assert resolved["group_by"] == []


def test_resolve_context_allows_metrics_with_group_by() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "obvodny",
        "filters": {"period": "may"},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "metrics": ["fact"],
                "group_by": ["article"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["metrics"] == ["fact"]
    assert resolved["group_by"] == ["article"]
    assert resolved["dimension"] is None


def test_resolve_context_article_grouping_clears_previous_article_filter() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["plan"],
        "filters": {"article": "ФОТ + налоги (ФОТ)", "article_kind": "detail"},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "context_query",
            "state_delta": {
                "group_by": ["article"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["group_by"] == ["article"]
    assert resolved["filters"] == {"article_kind": "detail"}
    assert resolved["project"] == "moskovsky"
    assert resolved["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"}


def test_resolve_context_clarification_answer_applies_delta() -> None:
    current_state = {
        "metrics": ["fact"],
        "awaiting_clarification": True,
        "clarification_target": "Уточните проект.",
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "clarification_answer",
            "state_delta": {
                "project": "obvodny",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny"
    assert resolved["metrics"] == ["fact"]
    assert resolved["awaiting_clarification"] is False
    assert resolved["clarification_target"] is None


def test_resolve_context_data_query_keeps_state_in_clarification_mode() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": None,
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
        "metrics": [],
        "filters": {"article": "реклама"},
        "awaiting_clarification": True,
        "clarification_target": "Уточните метрику для запроса.",
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "period": {"mode": "all"},
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["report_type"] == "payment_calendar"
    assert resolved["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май"}
    assert resolved["filters"] == {"article": "реклама"}
    assert resolved["metrics"] == ["fact"]
    assert resolved["awaiting_clarification"] is False
    assert resolved["clarification_target"] is None


def test_resolve_context_clarification_without_metrics_keeps_previous_metric() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "metrics": ["fact"],
        "filters": {"article": "marketing"},
        "awaiting_clarification": True,
        "clarification_target": "project?",
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "clarification_answer",
            "state_delta": {
                "project": "moskovsky",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "moskovsky"
    assert resolved["metrics"] == ["fact"]
    assert resolved["filters"] == {"article": "marketing"}


def test_set_clarification_state_stores_base_snapshot() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": None, "to": None, "label": "march"},
        "filters": {"article": "marketing"},
    }

    resolved = set_clarification_state(current_state, "metric?")

    assert resolved["awaiting_clarification"] is True
    assert resolved["clarification_target"] == "metric?"
    assert resolved["clarification_base_state"]["period"]["label"] == "march"
    assert resolved["clarification_base_state"]["filters"] == {"article": "marketing"}
    assert resolved["clarification_base_state"]["awaiting_clarification"] is False


def test_resolve_context_uses_clarification_base_snapshot() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": None, "to": None, "label": "whole period"},
        "metrics": [],
        "filters": {},
        "awaiting_clarification": True,
        "clarification_target": "metric?",
        "clarification_base_state": {
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": None, "to": None, "label": "march"},
            "metrics": [],
            "filters": {"article": "marketing"},
            "awaiting_clarification": False,
            "clarification_target": None,
        },
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "period": {"mode": "all"},
                "metrics": ["fact"],
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["last_intent"] == "clarification_answer"
    assert resolved["period"]["label"] == "march"
    assert resolved["filters"] == {"article": "marketing"}
    assert resolved["metrics"] == ["fact"]
    assert resolved["awaiting_clarification"] is False
    assert resolved["clarification_base_state"] is None


def test_resolve_context_report_type_clarification_keeps_collected_fields() -> None:
    current_state = {
        "metrics": ["fact"],
        "filters": {"article": "marketing"},
        "awaiting_clarification": True,
        "clarification_target": "report type?",
        "clarification_base_state": {
            "metrics": ["fact"],
            "filters": {"article": "marketing"},
            "awaiting_clarification": False,
            "clarification_target": None,
        },
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "clarification_answer",
            "state_delta": {
                "report_type": "payment_calendar",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["report_type"] == "payment_calendar"
    assert resolved["metrics"] == ["fact"]
    assert resolved["filters"] == {"article": "marketing"}
    assert resolved["awaiting_clarification"] is False


def test_resolve_context_new_view_query_exits_article_clarification() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
        "metrics": ["plan"],
        "filters": {"article": "ФОТ"},
        "awaiting_clarification": True,
        "clarification_target": "Уточните статью.",
        "clarification_kind": "article",
        "clarification_options": ["ФОТ + налоги (ФОТ)", "Реклама"],
        "clarification_base_state": {
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "metrics": ["plan"],
            "filters": {"article": "ФОТ"},
        },
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "period": {"label": "апрель"},
                "view": "details",
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["last_intent"] == "data_query"
    assert resolved["awaiting_clarification"] is False
    assert resolved["clarification_kind"] is None
    assert resolved["clarification_options"] == []
    assert resolved["view"] == "details"
    assert resolved["filters"] == {}
    assert resolved["period"]["label"] == "апрель"


def test_resolve_context_defaults_payment_calendar_article_query_to_all_metrics() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"label": "май"},
                "filters": {"article": "ФОТ"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context({}, parsed)

    assert resolved["metrics"] == ["plan", "fact", "deviation"]
    assert resolved["dimension"] is None


def test_resolve_context_does_not_default_bare_payment_calendar_period_to_all_metrics() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "period": {"label": "май"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context({}, parsed)

    assert resolved["metrics"] == []


def test_resolve_context_keeps_payment_calendar_dimension_query() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "dimension_query",
            "state_delta": {
                "report_type": "payment_calendar",
                "dimension": "article",
                "filters": {"article_kind": "detail"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context({}, parsed)

    assert resolved["last_intent"] == "dimension_query"
    assert resolved["dimension"] == "article"
    assert resolved["filters"] == {"article_kind": "detail"}
    assert resolved["metrics"] == []


def test_resolve_context_article_dimension_clears_previous_article_filter() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["plan"],
        "filters": {"article": "Реклама"},
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "dimension_query",
            "state_delta": {
                "dimension": "article",
                "filters": {"article_kind": "detail"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["last_intent"] == "dimension_query"
    assert resolved["dimension"] == "article"
    assert resolved["filters"] == {"article_kind": "detail"}
    assert resolved["project"] == "moskovsky"
    assert resolved["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"}
    assert resolved["metrics"] == []


def test_resolve_context_dimension_answer_keeps_dimension_query_intent() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "all",
        "metrics": [],
        "awaiting_clarification": True,
        "clarification_kind": "dimension",
        "clarification_target": "Что показать в платежном календаре?",
        "clarification_base_state": {
            "report_type": "payment_calendar",
            "project": "all",
            "metrics": [],
            "awaiting_clarification": False,
            "clarification_kind": None,
            "clarification_target": None,
        },
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "dimension_query",
            "state_delta": {
                "dimension": "article",
                "filters": {"article_kind": "detail"},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["last_intent"] == "dimension_query"
    assert resolved["dimension"] == "article"
    assert resolved["filters"] == {"article_kind": "detail"}
    assert resolved["metrics"] == []
    assert resolved["awaiting_clarification"] is False


def test_resolve_context_sets_clarification_state() -> None:
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "data_query",
            "state_delta": {
                "metrics": ["fact"],
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
        "project": "obvodny",
        "metrics": ["fact"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "math_on_last_result",
            "state_delta": {},
            "operation": {
                "type": "divide",
                "left": {"source": "last_result", "metric": "fact"},
                "right": {"source": "literal", "value": 2},
            },
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny"
    assert resolved["metrics"] == ["fact"]
    assert resolved["pending_operation"]["type"] == "divide"


def test_resolve_context_general_question_keeps_state() -> None:
    current_state = {
        "project": "obvodny",
        "metrics": ["fact"],
    }
    parsed = LLMParsedResponse.model_validate(
        {
            "intent": "general_question",
            "state_delta": {},
            "confidence": 0.9,
        },
    )

    resolved = resolve_context(current_state, parsed)

    assert resolved["project"] == "obvodny"
    assert resolved["metrics"] == ["fact"]
    assert resolved["last_intent"] == "general_question"
