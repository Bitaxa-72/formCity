from app.query_frame import DEFAULT_PERIOD_LABEL, build_query_frame


def test_build_query_frame_ready_with_defaults() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "metrics": ["revenue"],
        },
    )

    assert frame.ready is True
    assert frame.report_type == "summary"
    assert frame.project == "all"
    assert frame.period.label == DEFAULT_PERIOD_LABEL
    assert frame.metrics == ["revenue"]
    assert frame.missing_fields == []


def test_build_query_frame_missing_metric() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "project": "obvodny_118",
        },
    )

    assert frame.ready is False
    assert frame.missing_fields == ["metrics"]
    assert frame.clarification_question == "Уточните метрику для запроса."


def test_build_query_frame_not_ready_when_awaiting_clarification() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "metrics": ["revenue"],
            "awaiting_clarification": True,
            "clarification_target": "Уточните проект.",
        },
    )

    assert frame.ready is False
    assert frame.clarification_question == "Уточните проект."


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
            "project": "obvodny_118",
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
