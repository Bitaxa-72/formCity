from app.pipeline.forced_corrections import build_forced_parsed_response
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    build_failed_query_state,
)


def test_agents_context_takes_priority_over_stock_for_remaining_word() -> None:
    _state, parsed = build_forced_parsed_response(
        {"report_type": "agents_report"},
        "Славгородский остаток",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "agents_report"
    assert parsed.state_delta.metrics == ["agents_remaining_amount"]
    assert parsed.state_delta.filters == {"agent_contains": "Славгородский"}


def test_payment_calendar_failed_group_by_can_be_corrected_to_projects() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "group_by_not_supported_for_payment_calendar",
            FAILED_QUERY_STATE: {
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
                "metrics": ["plan"],
                "filters": {},
                "group_by": ["floor"],
            },
        },
        "по проектам",
    )

    assert parsed is not None
    assert state["project"] == "all"
    assert state["metrics"] == ["plan"]
    assert parsed.state_delta.group_by == ["project"]
    assert parsed.state_delta.project == "all"


def test_payment_calendar_explicit_unsupported_group_by_reaches_compatibility() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский план по этажам за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.project == "moskovsky"
    assert parsed.state_delta.period.label == "май"
    assert parsed.state_delta.metrics == ["plan"]
    assert parsed.state_delta.group_by == ["floor"]


def test_payment_calendar_context_takes_priority_over_stock_for_balance_end() -> None:
    _state, parsed = build_forced_parsed_response(
        {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        },
        "остаток на конец",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.view == "balance_end"


def test_payment_calendar_explicit_balance_start_takes_priority_over_stock() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский остаток на начало за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.project == "moskovsky"
    assert parsed.state_delta.period.label == "май"
    assert parsed.state_delta.view == "balance_start"


def test_payment_calendar_explicit_article_view_keeps_requested_period() -> None:
    _state, parsed = build_forced_parsed_response(
        {
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        },
        "платежный календарь план факт отклонение по статьям за март",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.period.label == "март"
    assert parsed.state_delta.view == "details"
    assert parsed.state_delta.metrics == ["plan", "fact", "deviation"]


def test_model_failed_metric_can_be_corrected_to_kpi() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "unknown_metric_for_model",
            FAILED_QUERY_STATE: {
                "report_type": "model",
                "project": "obvodny",
                "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"},
                "view": "model_summary",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        },
        "NPV",
    )

    assert parsed is not None
    assert state["report_type"] == "model"
    assert state["period"] == {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"}
    assert parsed.state_delta.metrics == ["model_npv"]


def test_payment_calendar_unsupported_metric_keeps_previous_successful_context() -> None:
    current_state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["plan"],
        "filters": {"article": "ФОТ + налоги (ФОТ)"},
    }
    resolved_state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
        "metrics": ["plan"],
        "filters": {"article": "выручка"},
    }

    failed_state = build_failed_query_state(
        current_state,
        resolved_state,
        "metric_not_supported_for_payment_calendar",
    )

    assert failed_state["filters"] == {"article": "ФОТ + налоги (ФОТ)"}


def test_payment_calendar_failed_metric_correction_uses_saved_successful_article() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "metric_not_supported_for_payment_calendar",
            FAILED_QUERY_STATE: {
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
                "metrics": ["plan"],
                "filters": {"article": "ФОТ + налоги (ФОТ)"},
                "group_by": [],
            },
        },
        "факт",
    )

    assert parsed is not None
    assert state["filters"] == {"article": "ФОТ + налоги (ФОТ)"}
    assert parsed.state_delta.metrics == ["fact"]
