from app.llm.parser_prompt import PARSER_SYSTEM_PROMPT


def test_parser_prompt_has_context_safety_rules() -> None:
    assert "Context safety rules" in PARSER_SYSTEM_PROMPT
    assert 'dialog_state.report_type="stock_for_sale"' in PARSER_SYSTEM_PROMPT
    assert 'view="stock_available_floors"' in PARSER_SYSTEM_PROMPT
    assert "сколько этажей?" in PARSER_SYSTEM_PROMPT
    assert "is unsupported" in PARSER_SYSTEM_PROMPT
