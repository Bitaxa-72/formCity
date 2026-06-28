from app.pipeline.forced_corrections import build_forced_parsed_response


def test_agents_context_takes_priority_over_stock_for_remaining_word() -> None:
    _state, parsed = build_forced_parsed_response(
        {"report_type": "agents_report"},
        "Славгородский остаток",
    )

    assert parsed is not None
    assert parsed.state_delta.report_type == "agents_report"
    assert parsed.state_delta.metrics == ["agents_remaining_amount"]
    assert parsed.state_delta.filters == {"agent_contains": "Славгородский"}
