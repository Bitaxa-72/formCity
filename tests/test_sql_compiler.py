import pytest

from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.sql_compiler import SQLCompileError, compile_sql


def test_compile_sql_builds_payment_calendar_total_fact() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
            "filters": {"article_kind": "payment_total"},
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.table == "payment_calendar_facts"
    assert query.metrics == ["fact"]
    assert query.group_by == []
    assert query.params == {"project": "obvodny", "filter_article_kind": "payment_total"}
    assert "SUM(fact_amount) AS fact" in query.sql
    assert "SUM(plan_amount) AS plan" in query.sql
    assert "SUM(deviation_amount) AS deviation" in query.sql
    assert "COUNT(*) AS source_rows" in query.sql
    assert "WHERE project = :project" in query.sql
    assert "article_kind = :filter_article_kind" in query.sql


def test_compile_sql_adds_period_and_filter_params() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "all",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
            },
            "metrics": ["fact"],
            "filters": {"article_kind": ["payment_total", "income_total"]},
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.group_by == ["project"]
    assert query.params == {
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "filter_article_kind_0": "payment_total",
        "filter_article_kind_1": "income_total",
    }
    assert "period_month >= :date_from" in query.sql
    assert "period_month <= :date_to" in query.sql
    assert "article_kind IN (:filter_article_kind_0, :filter_article_kind_1)" in query.sql
    assert "project AS project" in query.sql
    assert "GROUP BY project" in query.sql


def test_compile_sql_builds_payment_calendar_by_article() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
            },
            "metrics": ["plan", "fact", "deviation"],
            "filters": {"article_kind": "payment_total"},
            "group_by": ["metric"],
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.table == "payment_calendar_facts"
    assert query.params == {
        "project": "moskovsky",
        "date_from": "2026-03-01",
        "date_to": "2026-03-31",
        "filter_article_kind": "payment_total",
    }
    assert "period_month >= :date_from" in query.sql
    assert "period_month <= :date_to" in query.sql
    assert "article_kind = :filter_article_kind" in query.sql
    assert "article AS metric" in query.sql


def test_compile_sql_builds_payment_calendar_by_article_group() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {
                "from": "2026-05-01",
                "to": "2026-05-31",
            },
            "metrics": ["plan", "fact", "deviation"],
            "filters": {"article_kind": "detail"},
            "group_by": ["article"],
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.metrics == ["plan", "fact", "deviation"]
    assert query.group_by == ["article"]
    assert query.params == {
        "project": "obvodny",
        "date_from": "2026-05-01",
        "date_to": "2026-05-31",
        "filter_article_kind": "detail",
    }
    assert "article AS article" in query.sql
    assert "SUM(plan_amount) AS plan" in query.sql
    assert "SUM(fact_amount) AS fact" in query.sql
    assert "SUM(deviation_amount) AS deviation" in query.sql
    assert "GROUP BY article" in query.sql


def test_compile_sql_builds_article_list_query() -> None:
    frame = build_query_frame(
        {
            "last_intent": "dimension_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "dimension": "article",
            "filters": {"article_kind": "detail"},
        },
    )
    metric_resolution = resolve_metrics(frame)

    query = compile_sql(frame, metric_resolution)

    assert query.table == "payment_calendar_facts"
    assert query.metrics == []
    assert query.group_by == ["article"]
    assert query.params == {"project": "obvodny", "filter_article_kind": "detail"}
    assert query.sql == (
        "SELECT DISTINCT\n"
        "  article AS article\n"
        "FROM payment_calendar_facts\n"
        "WHERE project = :project\n"
        "  AND article_kind = :filter_article_kind\n"
        "ORDER BY article"
    )


def test_compile_sql_rejects_not_ready_frame() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
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
            "metrics": ["fact"],
            "group_by": ["floor"],
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
                "left": {"source": "last_result", "metric": "fact"},
                "right": {"source": "literal", "value": 2},
            },
        },
    )
    metric_resolution = resolve_metrics(frame)

    with pytest.raises(SQLCompileError, match="operation_query_not_supported"):
        compile_sql(frame, metric_resolution)
