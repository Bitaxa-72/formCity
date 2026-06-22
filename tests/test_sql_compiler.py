import pytest

from app.metric_resolver import resolve_metrics
from app.query_frame import build_query_frame
from app.sql_compiler import SQLCompileError, compile_sql


def test_compile_sql_builds_sales_revenue_by_floor() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "obvodny_118",
            "metrics": ["revenue"],
            "group_by": ["floor"],
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.table == "sales_facts"
    assert query.metrics == ["revenue"]
    assert query.group_by == ["floor"]
    assert query.params == {"project": "obvodny_118"}
    assert query.sql == (
        "SELECT\n"
        "  floor AS floor,\n"
        "  SUM(revenue_amount) AS revenue\n"
        "FROM sales_facts\n"
        "WHERE project = :project\n"
        "GROUP BY floor"
    )


def test_compile_sql_adds_period_and_filter_params() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "all",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
            },
            "metrics": ["deal_count"],
            "filters": {"room_type": ["studio", "one_room"]},
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.params == {
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "filter_room_type_0": "studio",
        "filter_room_type_1": "one_room",
    }
    assert "deal_date >= :date_from" in query.sql
    assert "deal_date <= :date_to" in query.sql
    assert "room_type IN (:filter_room_type_0, :filter_room_type_1)" in query.sql


def test_compile_sql_rejects_not_ready_frame() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
        },
    )
    metric_resolution = resolve_metrics(frame)

    with pytest.raises(SQLCompileError, match="query_frame_not_ready"):
        compile_sql(frame, metric_resolution)


def test_compile_sql_rejects_invalid_metric_resolution() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)

    with pytest.raises(SQLCompileError, match="metric_resolution_not_valid"):
        compile_sql(frame, metric_resolution)


def test_compile_sql_rejects_operation_query() -> None:
    frame = build_query_frame(
        {
            "last_intent": "math_on_last_result",
            "pending_operation": {
                "type": "divide",
                "left": {"source": "last_result", "metric": "revenue"},
                "right": {"source": "literal", "value": 2},
            },
        },
    )
    metric_resolution = resolve_metrics(frame)

    with pytest.raises(SQLCompileError, match="operation_query_not_supported"):
        compile_sql(frame, metric_resolution)
