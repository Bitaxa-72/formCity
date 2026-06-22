from app.calculation_engine import CalculationResult
from app.response_data import MAX_TABLE_ROWS, build_response_data
from app.result_verifier import ResultVerification


def create_verification(verified: bool = True) -> ResultVerification:
    return ResultVerification(
        verified=verified,
        errors=[] if verified else ["empty_result"],
        warnings=[],
        row_count=1,
        metrics=["revenue"],
        columns=["project", "revenue"],
        source={
            "report_type": "sales_report",
            "project": "obvodny_118",
            "period": {"from": None, "to": None, "label": "весь доступный период"},
            "metrics": ["revenue"],
            "units": {"revenue": "rub"},
            "kind": "sql_result",
        },
    )


def test_build_response_data_returns_summary_and_table() -> None:
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=[{"project": "obvodny_118", "revenue": 150.26}],
        row_count=1,
        metrics=["revenue"],
        columns=["project", "revenue"],
    )

    response_data = build_response_data(calculation_result, create_verification())

    assert response_data.ready is True
    assert response_data.title == "Выручка: sales_report, obvodny_118"
    assert response_data.summary[0].label == "Выручка"
    assert response_data.summary[0].value == 150.26
    assert response_data.summary[0].unit == "руб."
    assert response_data.table is not None
    assert response_data.table.rows == [{"project": "obvodny_118", "revenue": 150.26}]
    assert response_data.errors == []


def test_build_response_data_limits_table_rows() -> None:
    rows = [{"revenue": index} for index in range(MAX_TABLE_ROWS + 2)]
    calculation_result = CalculationResult(
        kind="sql_result",
        rows=rows,
        row_count=len(rows),
        metrics=["revenue"],
        columns=["revenue"],
    )

    response_data = build_response_data(calculation_result, create_verification())

    assert response_data.table is not None
    assert len(response_data.table.rows) == MAX_TABLE_ROWS
    assert response_data.table.total_rows == MAX_TABLE_ROWS + 2
    assert response_data.table.truncated is True


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
    assert response_data.source["report_type"] == "sales_report"
