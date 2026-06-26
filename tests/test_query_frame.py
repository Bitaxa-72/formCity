from app.pipeline.query_frame import (
    DEFAULT_PERIOD_LABEL,
    DIMENSION_CLARIFICATION,
    NON_DATA_QUERY_MESSAGE,
    REPORT_TYPE_CLARIFICATION,
    build_query_frame,
)


def test_build_query_frame_requires_report_type() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "metrics": ["revenue"],
        },
    )

    assert frame.ready is False
    assert frame.report_type is None
    assert frame.project == "all"
    assert frame.period.label == DEFAULT_PERIOD_LABEL
    assert frame.metrics == ["revenue"]
    assert frame.missing_fields == ["report_type"]
    assert frame.clarification_question == REPORT_TYPE_CLARIFICATION


def test_build_query_frame_missing_metric() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "obvodny",
        },
    )

    assert frame.ready is False
    assert frame.missing_fields == ["metrics"]
    assert frame.clarification_question == "Уточните метрику для запроса."


def test_build_query_frame_accepts_payment_calendar_view_without_metric() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "all",
            "view": "summary",
        },
    )

    assert frame.ready is True
    assert frame.view == "summary"
    assert frame.missing_fields == []


def test_build_query_frame_dimension_query_requires_dimension() -> None:
    frame = build_query_frame(
        {
            "last_intent": "dimension_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
        },
    )

    assert frame.ready is False
    assert frame.missing_fields == ["dimension"]
    assert frame.clarification_question == DIMENSION_CLARIFICATION


def test_build_query_frame_dimension_query_ready() -> None:
    frame = build_query_frame(
        {
            "last_intent": "dimension_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "dimension": "article",
            "filters": {"article_kind": "detail"},
        },
    )

    assert frame.ready is True
    assert frame.dimension == "article"
    assert frame.filters == {"article_kind": "detail"}


def test_build_query_frame_not_ready_when_awaiting_clarification() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "metrics": ["revenue"],
            "awaiting_clarification": True,
            "clarification_target": "Уточните проект.",
        },
    )

    assert frame.ready is False
    assert frame.clarification_question == "Уточните проект."


def test_build_query_frame_prefers_backend_clarification_for_missing_fields() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "awaiting_clarification": True,
            "clarification_target": "What data would you like to query?",
        },
    )

    assert frame.ready is False
    assert frame.missing_fields == ["report_type", "metrics"]
    assert frame.clarification_question == REPORT_TYPE_CLARIFICATION


def test_build_query_frame_math_operation_ready() -> None:
    frame = build_query_frame(
        {
            "last_intent": "math_on_last_result",
            "metrics": ["revenue"],
            "pending_operation": {
                "type": "divide",
                "left": {"source": "last_result", "metric": "revenue"},
                "right": {"source": "literal", "value": 2},
            },
        },
    )

    assert frame.ready is True
    assert frame.operation is not None
    assert frame.operation["type"] == "divide"


def test_build_query_frame_keeps_group_by_and_filters() -> None:
    frame = build_query_frame(
        {
            "last_intent": "context_query",
            "report_type": "sales_report",
            "project": "obvodny",
            "period": {"from": "2026-03-01", "to": "2026-03-31"},
            "metrics": ["revenue"],
            "filters": {"room_type": "apartments"},
            "group_by": ["floor"],
        },
    )

    assert frame.ready is True
    assert frame.report_type == "sales_report"
    assert frame.period.from_date == "2026-03-01"
    assert frame.filters == {"room_type": "apartments"}
    assert frame.group_by == ["floor"]


def test_build_query_frame_adds_project_group_for_all_project_metric_query() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": "2026-03-01", "to": "2026-03-31"},
            "metrics": ["fact"],
        },
    )

    assert frame.ready is True
    assert frame.project == "all"
    assert frame.group_by == ["project"]


def test_build_query_frame_blocks_unsupported_intent_even_with_existing_context() -> None:
    frame = build_query_frame(
        {
            "last_intent": "unsupported",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "metrics": ["plan"],
            "filters": {"article": "ФОТ + налоги (ФОТ)"},
        },
    )

    assert frame.ready is False
    assert frame.missing_fields == ["intent"]
    assert frame.clarification_question == NON_DATA_QUERY_MESSAGE
