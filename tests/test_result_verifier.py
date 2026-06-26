from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.result_verifier import verify_result


def test_verify_result_accepts_valid_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "obvodny", "fact": 100}],
        row_count=1,
        metrics=["fact"],
        columns=["project", "fact"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is True
    assert verification.errors == []
    assert verification.source["report_type"] == "payment_calendar"
    assert verification.source["units"] == {"fact": "rub"}


def test_verify_result_rejects_missing_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)

    verification = verify_result(frame, metric_resolution, None)

    assert verification.verified is False
    assert verification.errors == ["result_missing"]
    assert verification.row_count == 0


def test_verify_result_rejects_empty_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[],
        row_count=0,
        metrics=["fact"],
        columns=["fact"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["empty_result"]


def test_verify_result_rejects_empty_aggregate_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"fact": None, "source_rows": 0}],
        row_count=1,
        metrics=["fact"],
        columns=["fact", "source_rows"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["empty_result"]


def test_verify_result_warns_about_missing_metric_value() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"plan": 2900000, "fact": None, "deviation": None, "source_rows": 1}],
        row_count=1,
        metrics=["fact"],
        columns=["plan", "fact", "deviation", "source_rows"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is True
    assert verification.warnings == ["metric_value_missing"]
    assert verification.source["missing_metrics"] == ["fact"]


def test_verify_result_rejects_missing_metric_column() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"plan": 10}],
        row_count=1,
        metrics=["plan"],
        columns=["plan"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["metric_column_missing"]


def test_verify_result_rejects_project_mismatch() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "moskovsky", "fact": 100}],
        row_count=1,
        metrics=["fact"],
        columns=["project", "fact"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["project_mismatch"]


def test_verify_result_rejects_period_out_of_range() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
            },
            "metrics": ["fact"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"period_month": "2026-04-01", "fact": 100}],
        row_count=1,
        metrics=["fact"],
        columns=["period_month", "fact"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["period_out_of_range"]
