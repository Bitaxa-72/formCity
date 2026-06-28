from app.llm.answer import build_fallback_answer
from app.pipeline.response_data import ResponseData


def test_build_fallback_answer_does_not_add_unit_to_missing_summary_value() -> None:
    response_data = ResponseData(
        ready=True,
        title="payment_calendar",
        summary=[
            {"metric": "plan", "label": "plan", "value": 2900000, "unit": "rub"},
            {"metric": "fact", "label": "fact", "value": None, "unit": "rub"},
            {"metric": "deviation", "label": "deviation", "value": None, "unit": "rub"},
        ],
        table=None,
        source={
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
            "filters": {"article": "Реклама"},
            "metrics": ["plan", "fact", "deviation"],
        },
        warnings=["metric_value_missing"],
        errors=[],
    )

    draft = build_fallback_answer(response_data)

    assert "План: 2 900 000 руб." in draft.text
    assert "Факт: нет данных" in draft.text
    assert "Отклонение: нет данных" in draft.text
    assert "нет данных руб." not in draft.text
