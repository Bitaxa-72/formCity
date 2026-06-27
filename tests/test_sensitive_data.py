from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.response_data import build_response_data
from app.pipeline.result_verifier import ResultVerification
from app.pipeline.sensitive_data import sanitize_text, visible_rows


def test_sensitive_rows_are_hidden_from_response_data() -> None:
    result = CalculationResult(
        kind="sql_result",
        rows=[
            {"metric": "revenue", "value": 10, "is_sensitive": False},
            {"metric": "phone", "value": "+7 999 111-22-33", "is_sensitive": True},
        ],
        row_count=2,
        metrics=["value"],
        columns=["metric", "value", "is_sensitive"],
    )
    verification = ResultVerification(
        verified=True,
        errors=[],
        warnings=[],
        row_count=2,
        metrics=["value"],
        columns=["metric", "value", "is_sensitive"],
        source={"report_type": "model"},
    )

    response = build_response_data(result, verification)

    assert response.table is not None
    assert response.table.total_rows == 1
    assert response.table.rows == [{"metric": "revenue", "value": 10}]
    assert response.table.columns == ["metric", "value"]


def test_sensitive_columns_are_hidden_and_text_values_are_masked() -> None:
    rows = visible_rows(
        [
            {
                "name": "manager",
                "phone": "+7 999 111-22-33",
                "document_number": "AB12345",
                "note": "email test@example.com, doc № 12345",
            },
        ],
    )

    assert rows == [{"name": "manager", "note": "email [контакт скрыт], doc № [номер документа скрыт]"}]


def test_sanitize_text_masks_contacts() -> None:
    assert sanitize_text("phone +7 999 111-22-33 and a@b.ru") == "phone [контакт скрыт] and [контакт скрыт]"


def test_sanitize_text_does_not_mask_decimal_numbers() -> None:
    text = "Коэффициент: 0.665766986557602, сумма: 123456789.12"

    sanitized = sanitize_text(text)

    assert "0.665766986557602" in sanitized
    assert "123456789.12" in sanitized
    assert "[контакт скрыт]" not in sanitized


def test_sanitize_text_masks_person_names() -> None:
    text = "Ответственный Романников С.В., клиент Иванов Иван Иванович"

    sanitized = sanitize_text(text)

    assert "Романников" not in sanitized
    assert "Иванов Иван Иванович" not in sanitized
    assert sanitized.count("[скрыто]") == 2
