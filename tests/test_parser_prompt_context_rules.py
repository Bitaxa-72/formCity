from app.llm.parser_prompt import PARSER_SYSTEM_PROMPT


def test_parser_prompt_has_context_safety_rules() -> None:
    assert "Context safety rules" in PARSER_SYSTEM_PROMPT
    assert 'dialog_state.report_type="stock_for_sale"' in PARSER_SYSTEM_PROMPT
    assert 'view="stock_available_floors"' in PARSER_SYSTEM_PROMPT
    assert "сколько этажей?" in PARSER_SYSTEM_PROMPT
    assert "is unsupported" in PARSER_SYSTEM_PROMPT


def test_parser_prompt_keeps_partial_analytics_without_report_type() -> None:
    assert "asks for analytics fields like metric, period, entity, category, article, or filter" in PARSER_SYSTEM_PROMPT
    assert 'User: "факт по рекламе за май"' in PARSER_SYSTEM_PROMPT
    assert '"metrics": ["fact"]' in PARSER_SYSTEM_PROMPT
    assert '"filters": {"article": "реклама"}' in PARSER_SYSTEM_PROMPT
