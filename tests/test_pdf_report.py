from app.pipeline.pdf_report import column_label, format_value, visible_columns
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
