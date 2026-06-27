import pytest

from app.pipeline.text_intents import is_capabilities_question


@pytest.mark.parametrize(
    "text",
    [
        "что ты умеешь?",
        "какие отчеты доступны?",
        "какие отчеты есть?",
        "какие данные есть?",
        "как пользоваться ботом?",
        "помоги",
        "help",
        "что можно спросить?",
    ],
)
def test_capabilities_questions_use_backend_answer(text: str) -> None:
    assert is_capabilities_question(text) is True
