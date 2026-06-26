from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.response_data import MAX_TABLE_ROWS, build_response_data
from app.pipeline.result_verifier import ResultVerification


def create_verification(verified: bool = True) -> ResultVerification:
    return ResultVerification(
        verified=verified,
        errors=[] if verified else ["empty_result"],
        warnings=[],
        row_count=1,
        metrics=["fact"],
        columns=["project", "fact"],
        source={
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": {"from": None, "to": None, "label": "весь доступный период"},
            "metrics": ["fact"],
            "units": {"fact": "rub"},
            "kind": "sql_result",
        },
    )


def test_build_response_data_returns_summary_and_table() -> None:
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "obvodny", "fact": 150.26}],
        row_count=1,
        metrics=["fact"],
        columns=["project", "fact"],
    )

    response_data = build_response_data(calculation_result, create_verification())

    assert response_data.ready is True
    assert response_data.title == "Факт: payment_calendar, obvodny"
    assert response_data.summary[0].label == "Факт"
    assert response_data.summary[0].value == 150.26
    assert response_data.summary[0].unit == "руб."
    assert response_data.table is not None
    assert response_data.table.rows == [{"project": "obvodny", "fact": 150.26}]
    assert response_data.errors == []


def test_build_response_data_limits_table_rows() -> None:
    rows = [{"fact": index} for index in range(MAX_TABLE_ROWS + 2)]
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=rows,
        row_count=len(rows),
        metrics=["fact"],
        columns=["fact"],
    )

    response_data = build_response_data(calculation_result, create_verification())

    assert response_data.table is not None
    assert len(response_data.table.rows) == MAX_TABLE_ROWS
    assert response_data.table.total_rows == MAX_TABLE_ROWS + 2
    assert response_data.table.truncated is True


def test_build_response_data_hides_internal_columns() -> None:
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"plan": 2900000, "fact": None, "source_rows": 1}],
        row_count=1,
        metrics=["fact"],
        columns=["plan", "fact", "source_rows"],
    )

    response_data = build_response_data(calculation_result, create_verification())

    assert response_data.table is not None
    assert response_data.table.columns == ["plan", "fact"]
    assert response_data.table.rows == [{"plan": 2900000, "fact": None}]


def test_build_response_data_rejects_missing_verification() -> None:
    response_data = build_response_data(None, None)

    assert response_data.ready is False
    assert response_data.errors == ["verification_missing"]
    assert response_data.table is None


def test_build_response_data_rejects_missing_result() -> None:
    verification = create_verification(verified=False)

    response_data = build_response_data(None, verification)

    assert response_data.ready is False
    assert response_data.errors == ["empty_result"]
    assert response_data.source["report_type"] == "payment_calendar"
