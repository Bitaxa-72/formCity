from app.pipeline.metric_resolver import REPORT_NOT_CONNECTED_MESSAGE, resolve_metrics
from app.pipeline.query_frame import build_query_frame


def test_resolve_metrics_accepts_payment_calendar_fact() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
            "filters": {"article_kind": "payment_total"},
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is True
    assert resolution.errors == []
    assert resolution.metrics[0].name == "fact"
    assert resolution.metrics[0].unit == "rub"


def test_resolve_metrics_rejects_unknown_report_type() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "unknown",
            "metrics": ["fact"],
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is False
    assert resolution.errors == ["unknown_report_type"]
    assert resolution.clarification_question == "Уточните тип отчета."


def test_resolve_metrics_rejects_metric_for_summary_report_type() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "summary",
            "metrics": ["fact"],
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is False
    assert resolution.errors == ["metric_not_allowed_for_report_type"]
    assert resolution.clarification_question == REPORT_NOT_CONNECTED_MESSAGE


def test_resolve_metrics_rejects_metric_for_connected_report_type() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["revenue"],
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is False
    assert resolution.errors == ["metric_not_allowed_for_report_type"]
    assert resolution.clarification_question == REPORT_NOT_CONNECTED_MESSAGE


def test_resolve_metrics_rejects_group_by_for_metric() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["plan"],
            "group_by": ["floor"],
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is False
    assert resolution.errors == ["group_by_not_allowed_for_metric"]


def test_resolve_metrics_rejects_filter_for_metric() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
            "filters": {"unknown_filter": "value"},
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is False
    assert resolution.errors == ["filter_not_allowed_for_metric"]


def test_resolve_metrics_skips_catalog_for_operation() -> None:
    frame = build_query_frame(
        {
            "last_intent": "math_on_last_result",
            "pending_operation": {
                "type": "divide",
                "left": {"source": "last_result", "metric": "fact"},
                "right": {"source": "literal", "value": 2},
            },
        },
    )

    resolution = resolve_metrics(frame)

    assert resolution.valid is True
    assert resolution.errors == []
