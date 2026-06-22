import pytest
from pydantic import ValidationError

from app.llm_answer import AnswerDraft, build_unready_answer
from app.response_data import ResponseData


def test_answer_draft_accepts_valid_payload() -> None:
    draft = AnswerDraft.model_validate(
        {
            "text": "Выручка по проекту Обводный 118 составила 150.26 руб.",
            "used_metrics": ["revenue"],
            "source": {"report_type": "sales_report"},
            "warnings": [],
        },
    )

    assert draft.text == "Выручка по проекту Обводный 118 составила 150.26 руб."
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
