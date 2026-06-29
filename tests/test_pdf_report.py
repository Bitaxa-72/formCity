from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.pdf_report import build_pdf_report, column_label, format_value, visible_columns
from app.pipeline.result_verifier import ResultVerification
from app.pipeline.sensitive_data import visible_rows


def test_visible_columns_hides_internal_source_rows() -> None:
    assert visible_columns(["article", "plan", "fact", "source_rows"]) == ["article", "plan", "fact"]


def test_column_label_uses_russian_names() -> None:
    assert column_label("article") == "Статья"
    assert column_label("plan") == "План"
    assert column_label("fact") == "Факт"
    assert column_label("deviation") == "Отклонение"


def test_format_value_prints_payment_calendar_values() -> None:
    assert format_value("project", "moskovsky") == "Московский"
    assert format_value("article_kind", "payment_total") == "Итого платежи"
    assert format_value("fact", 2520223) == "2 520 223 руб."
    assert format_value("article", "ИП Иванов И.") == "ИП Иванов И."


def test_visible_rows_keeps_payment_calendar_article_name() -> None:
    rows = visible_rows([{"article": "ИП Иванов И.", "plan": 100}])

    assert rows == [{"article": "ИП Иванов И.", "plan": 100}]


def test_visible_rows_keeps_agent_name_for_reports() -> None:
    rows = visible_rows(
        [
            {
                "agent_name": "ИП Иванов И.",
                "buyer_name": "Петров Петр Петрович",
            },
        ],
    )

    assert rows == [{"agent_name": "ИП Иванов И.", "buyer_name": "[скрыто]"}]


def test_model_raw_rows_pdf_handles_long_values_preview() -> None:
    calculation = CalculationResult(
        kind="sql_result",
        rows=[
            {
                "raw_sheet": "Финмодель",
                "row_number": index,
                "row_label": f"Строка {index}",
                "visible_cells": 10,
                "values_preview": " | ".join(f"C{cell}: значение {cell} " + "x" * 80 for cell in range(20)),
            }
            for index in range(1, 40)
        ],
        columns=["raw_sheet", "row_number", "row_label", "visible_cells", "values_preview"],
        row_count=39,
        metrics=[],
    )
    verification = ResultVerification(
        verified=True,
        errors=[],
        warnings=[],
        row_count=39,
        metrics=[],
        columns=calculation.columns,
        source={
            "report_type": "model",
            "view": "model_raw_rows",
            "project": "obvodny",
            "period": {"label": "апрель 2026"},
            "filters": {"raw_sheet": "financial_model"},
        },
    )

    pdf_bytes, filename = build_pdf_report(calculation, verification)

    assert filename == "model.pdf"
    assert pdf_bytes.startswith(b"%PDF")
