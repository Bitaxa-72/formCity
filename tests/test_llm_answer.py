import asyncio

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.llm.answer import AnswerDraft, OpenAILLMAnswerer, build_fallback_answer, build_unready_answer, validate_answer_payload
from app.pipeline.response_data import ResponseData


def test_answer_draft_accepts_valid_payload() -> None:
    draft = AnswerDraft.model_validate(
        {
            "text": "Выручка по проекту Обводный составила 150.26 руб.",
            "used_metrics": ["revenue"],
            "source": {"report_type": "sales_report"},
            "warnings": [],
        },
    )

    assert draft.text == "Выручка по проекту Обводный составила 150.26 руб."
    assert draft.used_metrics == ["revenue"]


def test_answer_draft_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AnswerDraft.model_validate(
            {
                "text": "Ответ",
                "used_metrics": [],
                "source": {},
                "warnings": [],
                "new_number": 999,
            },
        )


def test_validate_answer_payload_accepts_message_alias() -> None:
    draft = validate_answer_payload(
        {"message": "Здравствуйте.", "extra": "ignored"},
        "invalid",
    )

    assert draft.text == "Здравствуйте."
    assert draft.used_metrics == []
    assert draft.source == {}
    assert draft.warnings == []


def test_build_unready_answer_uses_response_errors() -> None:
    response_data = ResponseData(
        ready=False,
        title="Результат отсутствует",
        summary=[],
        table=None,
        source={"report_type": "sales_report"},
        warnings=[],
        errors=["result_missing"],
    )

    draft = build_unready_answer(response_data)

    assert draft.text == "Не удалось подготовить проверенный ответ по данным."
    assert draft.used_metrics == []
    assert draft.source == {"report_type": "sales_report"}
    assert draft.warnings == ["result_missing"]


def test_build_unready_answer_handles_missing_response_data() -> None:
    draft = build_unready_answer(None)

    assert draft.warnings == ["response_data_missing"]
    assert draft.source == {}


def test_build_fallback_answer_explains_missing_metric_value() -> None:
    response_data = ResponseData(
        ready=True,
        title="Факт: payment_calendar, all",
        summary=[
            {
                "metric": "fact",
                "label": "Факт",
                "value": None,
                "unit": "руб.",
            },
        ],
        table={
            "columns": ["plan", "fact", "deviation"],
            "rows": [{"plan": 2900000, "fact": None, "deviation": None}],
            "total_rows": 1,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "filters": {"article": "Реклама"},
            "metrics": ["fact"],
            "units": {"fact": "rub"},
            "missing_metrics": ["fact"],
        },
        warnings=["metric_value_missing"],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert draft.text == (
        'По статье "Реклама" за май 2026 факт не заполнен.\n'
        "План: 2 900 000 руб.\n"
        "Факт: нет данных\n"
        "Отклонение: нет данных"
    )
    assert draft.used_metrics == ["fact"]


def test_build_fallback_answer_does_not_explain_missing_metric_for_metric_bundle() -> None:
    response_data = ResponseData(
        ready=True,
        title="План, Факт, Отклонение: payment_calendar, all",
        summary=[],
        table={
            "columns": ["plan", "fact", "deviation"],
            "rows": [{"plan": 2900000, "fact": None, "deviation": None}],
            "total_rows": 1,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "filters": {"article": "Реклама"},
            "metrics": ["plan", "fact", "deviation"],
            "units": {"plan": "rub", "fact": "rub", "deviation": "rub"},
            "missing_metrics": ["fact", "deviation"],
        },
        warnings=["metric_value_missing"],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert draft.text == (
        "Платежный календарь\n"
        "Проект: Московский\n"
        "Период: май 2026\n"
        "Статья: Реклама\n"
        "\n"
        "План: 2 900 000 руб.\n"
        "Факт: нет данных\n"
        "Отклонение: нет данных"
    )
    assert "нет данных руб." not in draft.text


def test_build_fallback_answer_formats_payment_calendar_header() -> None:
    response_data = ResponseData(
        ready=True,
        title="Факт: payment_calendar, moskovsky",
        summary=[
            {
                "metric": "fact",
                "label": "Факт",
                "value": 2520223,
                "unit": "руб.",
            },
        ],
        table={
            "columns": ["fact"],
            "rows": [{"fact": 2520223}],
            "total_rows": 1,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель"},
            "filters": {"article": "Реклама"},
            "metrics": ["fact"],
            "units": {"fact": "rub"},
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert draft.text == (
        "Платежный календарь\n"
        "Проект: Московский\n"
        "Период: апрель 2026\n"
        "Статья: Реклама\n"
        "\n"
        "Факт: 2 520 223 руб."
    )


def test_build_fallback_answer_prints_project_rows() -> None:
    response_data = ResponseData(
        ready=True,
        title="Факт: payment_calendar, all",
        summary=[
            {
                "metric": "fact",
                "label": "Факт",
                "value": 100,
                "unit": "руб.",
            },
        ],
        table={
            "columns": ["project", "fact"],
            "rows": [
                {"project": "moskovsky", "fact": 100},
                {"project": "obvodny", "fact": 200},
            ],
            "total_rows": 2,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": "2026-03-01", "to": "2026-03-31", "label": "март"},
            "metrics": ["fact"],
            "units": {"fact": "rub"},
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert draft.text.startswith("Платежный календарь\nПериод: март 2026\n\n")
    assert "payment_calendar, all" not in draft.text
    assert "Проект: Московский:" in draft.text
    assert "Факт: 100 руб." in draft.text
    assert "Проект: Обводный:" in draft.text
    assert "Факт: 200 руб." in draft.text
    assert draft.used_metrics == ["fact"]


def test_build_fallback_answer_prints_payment_calendar_article_kind_labels() -> None:
    response_data = ResponseData(
        ready=True,
        title="Платежный календарь",
        summary=[],
        table={
            "columns": ["project", "article_kind", "plan", "fact", "deviation"],
            "rows": [
                {"project": "moskovsky", "article_kind": "payment_total", "plan": 10, "fact": 8, "deviation": -2},
                {"project": "moskovsky", "article_kind": "income_total", "plan": 20, "fact": 30, "deviation": 10},
            ],
            "total_rows": 2,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"from": "2026-03-01", "to": "2026-03-31", "label": "март"},
            "metrics": ["plan", "fact", "deviation"],
            "units": {"plan": "rub", "fact": "rub", "deviation": "rub"},
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert "Проект: Московский, Поступления:" in draft.text
    assert "Проект: Московский, Итого платежи:" in draft.text
    assert "income_total" not in draft.text
    assert "payment_total" not in draft.text


def test_build_fallback_answer_prints_article_kind_filter_as_section() -> None:
    response_data = ResponseData(
        ready=True,
        title="Платежный календарь",
        summary=[],
        table={
            "columns": ["plan", "fact", "deviation"],
            "rows": [{"plan": 10, "fact": 8, "deviation": -2}],
            "total_rows": 1,
            "truncated": False,
        },
        source={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "metrics": ["plan"],
            "filters": {"article_kind": "payment_total"},
            "units": {"plan": "rub"},
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert "Раздел: Итого платежи" in draft.text
    assert "Тип строки" not in draft.text


def test_build_fallback_answer_prints_dimension_project_list() -> None:
    response_data = ResponseData(
        ready=True,
        title="payment_calendar, all",
        summary=[],
        table={
            "columns": ["project"],
            "rows": [{"project": "moskovsky"}, {"project": "obvodny"}],
            "total_rows": 2,
            "truncated": False,
        },
        source={
            "intent": "dimension_query",
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"label": "весь доступный период"},
            "dimension": "project",
            "metrics": [],
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert draft.text == (
        "Платежный календарь\n"
        "Период: весь доступный период\n"
        "\n"
        "Проекты:\n"
        "- Московский\n"
        "- Обводный"
    )


def test_build_fallback_answer_prints_dimension_article_kind_list() -> None:
    response_data = ResponseData(
        ready=True,
        title="payment_calendar, all",
        summary=[],
        table={
            "columns": ["article_kind"],
            "rows": [{"article_kind": "income_total"}, {"article_kind": "payment_total"}, {"article_kind": "detail"}],
            "total_rows": 3,
            "truncated": False,
        },
        source={
            "intent": "dimension_query",
            "report_type": "payment_calendar",
            "project": "all",
            "period": {"label": "весь доступный период"},
            "dimension": "article_kind",
            "metrics": [],
        },
        warnings=[],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert "Разделы:" in draft.text
    assert "- Поступления" in draft.text
    assert "- Итого платежи" in draft.text
    assert "- Статья расходов" in draft.text


def test_openai_answerer_uses_template_for_summary_without_openai_key() -> None:
    response_data = ResponseData(
        ready=True,
        title="Сводный отчет",
        summary=[],
        table={
            "columns": ["project", "summary_sheet_count", "summary_row_count", "summary_cell_count"],
            "rows": [
                {
                    "project": "obvodny",
                    "summary_sheet_count": 3,
                    "summary_row_count": 120,
                    "summary_cell_count": 900,
                },
            ],
            "total_rows": 1,
            "truncated": False,
        },
        source={
            "report_type": "summary",
            "project": "obvodny",
            "metrics": ["summary_sheet_count", "summary_row_count", "summary_cell_count"],
        },
        warnings=[],
        errors=[],
    )

    answerer = OpenAILLMAnswerer(Settings(bot_token=None, allowed_usernames=set()))

    draft = asyncio.run(answerer.build_answer(response_data))

    assert "Сводный отчет" in draft.text
    assert "Количество листов: 3" in draft.text
    assert "Количество строк: 120" in draft.text
