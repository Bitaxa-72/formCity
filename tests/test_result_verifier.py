from app.calculation_engine import CalculationResult
from app.metric_resolver import resolve_metrics
from app.query_frame import build_query_frame
from app.result_verifier import verify_result


def test_verify_result_accepts_valid_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "obvodny_118",
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "obvodny_118", "revenue": 100}],
        row_count=1,
        metrics=["revenue"],
        columns=["project", "revenue"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is True
    assert verification.errors == []
    assert verification.source["report_type"] == "sales_report"
    assert verification.source["units"] == {"revenue": "rub"}


def test_verify_result_rejects_missing_result() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "metrics": ["revenue"],
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
            "report_type": "sales_report",
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[],
        row_count=0,
        metrics=["revenue"],
        columns=["revenue"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["empty_result"]


def test_verify_result_rejects_missing_metric_column() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"sold_area": 10}],
        row_count=1,
        metrics=["sold_area"],
        columns=["sold_area"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["metric_column_missing"]


def test_verify_result_rejects_project_mismatch() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "obvodny_118",
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "well_moskovsky", "revenue": 100}],
        row_count=1,
        metrics=["revenue"],
        columns=["project", "revenue"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["project_mismatch"]


def test_verify_result_rejects_period_out_of_range() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
            },
            "metrics": ["revenue"],
        },
    )
    metric_resolution = resolve_metrics(frame)
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"deal_date": "2026-04-01", "revenue": 100}],
        row_count=1,
        metrics=["revenue"],
        columns=["deal_date", "revenue"],
    )

    verification = verify_result(frame, metric_resolution, calculation_result)

    assert verification.verified is False
    assert verification.errors == ["period_out_of_range"]
