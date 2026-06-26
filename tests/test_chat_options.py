from app.llm.chat_options import build_chat_completion_options


def test_build_chat_completion_options_omits_temperature_for_gpt_5() -> None:
    assert build_chat_completion_options("gpt-5.5") == {}


def test_build_chat_completion_options_keeps_temperature_for_older_models() -> None:
    assert build_chat_completion_options("gpt-4o-mini") == {"temperature": 0}
