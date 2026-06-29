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


def test_model_source_sheet_context_turns_short_text_into_sheet_search() -> None:
    _state, parsed = build_forced_parsed_response(
        {
            "report_type": "model",
            "view": "model_raw_rows",
            "period": {"label": "апрель"},
            "filters": {"raw_sheet": "remains"},
        },
        "помещения",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type is None
    assert parsed.state_delta.view == "model_raw_search"
    assert parsed.state_delta.filters == {"raw_sheet": "remains", "raw_query": "помещения"}


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


def test_payment_calendar_metric_by_text_becomes_article_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский план по ФОТ за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.project == "moskovsky"
    assert parsed.state_delta.period.label == "май"
    assert parsed.state_delta.metrics == ["plan"]
    assert parsed.state_delta.filters == {"article": "фот"}
    assert parsed.state_delta.group_by == []


def test_payment_calendar_all_metrics_by_text_becomes_article_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский план факт отклонение по рекламе за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.metrics == ["plan", "fact", "deviation"]
    assert parsed.state_delta.filters == {"article": "рекламе"}
    assert parsed.state_delta.group_by == []


def test_payment_calendar_unknown_by_text_still_becomes_article_filter_for_domain_validation() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский план по космическая статья 123 за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.filters == {"article": "космическая статья 123"}
    assert parsed.state_delta.group_by == []


def test_payment_calendar_explicit_unsupported_metric_stays_in_payment_calendar() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь NPV апрель",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.period.label == "апрель"
    assert parsed.state_delta.filters == {"article": "NPV"}


def test_payment_calendar_explicit_sales_metric_stays_in_payment_calendar() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский сделки за май",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.project == "moskovsky"
    assert parsed.state_delta.period.label == "май"
    assert parsed.state_delta.filters == {"article": "количество сделок"}


def test_model_npv_still_routes_to_model_without_payment_calendar_marker() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "модель NPV апрель",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "model"
    assert parsed.state_delta.metrics == ["model_npv"]


def test_agents_deals_still_route_to_agents_report_without_payment_calendar_marker() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "отчет по агентам сделки апрель",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "agents_report"


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


def test_payment_calendar_ambiguous_balance_returns_start_and_end() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь московский остаток за май",
    )

    assert parsed is not None
    assert parsed.needs_clarification is False
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.project == "moskovsky"
    assert parsed.state_delta.period.label == "май"
    assert parsed.state_delta.filters == {"article_kind": ["balance_start", "balance_end"]}
    assert parsed.state_delta.group_by == ["article_kind"]


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


def test_payment_calendar_sections_question_becomes_article_kind_dimension() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "какие разделы есть в платежном календаре?",
    )

    assert parsed is not None
    assert parsed.intent == "dimension_query"
    assert parsed.state_delta.report_type == "payment_calendar"
    assert parsed.state_delta.dimension == "article_kind"


def test_roadmap_context_step_number_becomes_step_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {"report_type": "roadmap"},
        "что на этапе 7?",
    )

    assert parsed is not None
    assert parsed.state_delta.view == "step_details"
    assert parsed.state_delta.filters == {"step_no": 7}


def test_roadmap_explicit_step_number_becomes_step_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "дорожная карта этап 2",
    )

    assert parsed is not None
    assert parsed.state_delta.view == "step_details"
    assert parsed.state_delta.filters == {"step_no": 2}


def test_roadmap_reverse_step_number_becomes_step_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {"report_type": "roadmap"},
        "покажи 5 этап дорожной карты",
    )

    assert parsed is not None
    assert parsed.state_delta.view == "step_details"
    assert parsed.state_delta.filters == {"step_no": 5}


def test_roadmap_step_word_without_number_keeps_steps_view() -> None:
    _state, parsed = build_forced_parsed_response(
        {"report_type": "roadmap"},
        "какие этапы есть в дорожной карте?",
    )

    assert parsed is not None
    assert parsed.state_delta.view == "roadmap_steps"
    assert parsed.state_delta.filters == {}


def test_roadmap_unsupported_metric_keeps_priority_over_step_filter() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "дорожная карта выручка этап 2",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "roadmap"
    assert parsed.state_delta.metrics == ["duration_min"]
    assert parsed.state_delta.filters == {}


def test_roadmap_deals_stays_in_roadmap_for_compatibility() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "дорожная карта сделки",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "roadmap"
    assert parsed.state_delta.metrics == ["duration_min"]
    assert parsed.state_delta.filters == {}


def test_roadmap_sensitive_request_stays_in_roadmap_for_compatibility() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "дорожная карта телефоны участников",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "roadmap"
    assert parsed.state_delta.metrics == ["duration_min"]
    assert parsed.state_delta.filters == {}


def test_non_roadmap_step_number_does_not_force_roadmap() -> None:
    _state, parsed = build_forced_parsed_response(
        {},
        "платежный календарь этап 2",
    )

    assert parsed is None


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
    assert failed_state["project"] == "moskovsky"
    assert failed_state["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"}


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


def test_payment_calendar_failed_metric_correction_keeps_failed_project_and_period_for_view() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "metric_not_supported_for_payment_calendar",
            FAILED_QUERY_STATE: {
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"},
                "metrics": ["plan", "fact", "deviation"],
                "filters": {},
                "group_by": [],
            },
        },
        "поступления",
    )

    assert parsed is not None
    assert state["project"] == "moskovsky"
    assert state["period"] == {"from": "2026-05-01", "to": "2026-05-31", "label": "май 2026"}
    assert parsed.state_delta.view == "income"
    assert parsed.state_delta.filters == {}


def test_payment_calendar_failed_article_correction_keeps_article_when_period_changes() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "article_not_found",
            FAILED_QUERY_STATE: {
                "report_type": "payment_calendar",
                "project": "obvodny",
                "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель 2026"},
                "metrics": ["deviation"],
                "filters": {"article": "Реклама"},
                "group_by": [],
            },
            "pending_action": "show_available_articles",
            "pending_payload": {},
        },
        "февраль",
    )

    assert parsed is not None
    assert state["project"] == "obvodny"
    assert state["period"] == {"label": "февраль"}
    assert state["filters"] == {"article": "Реклама"}
    assert parsed.state_delta.period.label == "февраль"
    assert parsed.state_delta.metrics == ["deviation"]
    assert "pending_action" not in state


def test_payment_calendar_failed_article_correction_can_reset_article() -> None:
    state, parsed = build_forced_parsed_response(
        {
            CONTEXT_BLOCKED_AFTER_ERROR: True,
            FAILED_QUERY_ERROR: "article_not_found",
            FAILED_QUERY_STATE: {
                "report_type": "payment_calendar",
                "project": "obvodny",
                "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель 2026"},
                "metrics": ["deviation"],
                "filters": {"article": "Реклама"},
                "group_by": [],
            },
        },
        "в целом",
    )

    assert parsed is not None
    assert state["filters"] == {}
    assert parsed.state_delta.filters == {}
