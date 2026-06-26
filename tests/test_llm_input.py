from types import SimpleNamespace

from app.llm.input import build_dialog_state, build_last_result_summary, build_llm_input


def test_build_dialog_state_uses_defaults() -> None:
    state = build_dialog_state({})

    assert state.report_type is None
    assert state.period.from_date is None
    assert state.metrics == []
    assert state.awaiting_clarification is False


def test_build_dialog_state_accepts_context_values() -> None:
    state = build_dialog_state(
        {
            "report_type": "sales_report",
            "project": "obvodny",
            "period": {
                "from": "2026-03-01",
                "to": "2026-03-31",
                "label": "март 2026",
            },
            "metrics": ["revenue"],
            "view": "summary",
            "group_by": ["floor"],
        },
    )

    assert state.report_type == "sales_report"
    assert state.project == "obvodny"
    assert state.period.from_date == "2026-03-01"
    assert state.metrics == ["revenue"]
    assert state.view == "summary"
    assert state.group_by == ["floor"]


def test_build_last_result_summary_keeps_known_sections() -> None:
    summary = build_last_result_summary(
        {
            "metrics": {"revenue": {"value": 100, "unit": "rub"}},
            "project": "obvodny",
            "period": {"from": "2026-03-01", "to": "2026-03-31"},
        },
    )

    assert summary is not None
    assert summary["metrics"]["revenue"]["value"] == 100
    assert summary["project"] == "obvodny"
    assert summary["raw"] is None


def test_build_llm_input_collects_message_state_history_and_last_result() -> None:
    user_session = SimpleNamespace(
        state={
            "report_type": "sales_report",
            "project": "obvodny",
            "metrics": ["revenue"],
        },
        history=[
            SimpleNamespace(role="user", text="А подели на два"),
            SimpleNamespace(role="assistant", text="Выручка: 100"),
            SimpleNamespace(role="user", text="Сколько выручки?"),
        ],
        last_result={"metrics": {"revenue": {"value": 100, "unit": "rub"}}},
    )

    llm_input = build_llm_input("А подели на два", user_session, history_limit=2)

    assert llm_input.user_message == "А подели на два"
    assert llm_input.dialog_state.project == "obvodny"
    assert [item.text for item in llm_input.history] == ["Выручка: 100", "А подели на два"]
    assert llm_input.last_result_summary is not None
    assert "Return only valid JSON." in llm_input.system_rules
    assert "payment_calendar" in llm_input.dictionary["report_type"]
    assert "платежи" in llm_input.dictionary["report_type_aliases"]["payment_calendar"]
    assert llm_input.dictionary["report_rules"]["payment_calendar"]["metric_bundles"]["full"]["metrics"] == [
        "plan",
        "fact",
        "deviation",
    ]
    assert llm_input.dictionary["report_rules"]["payment_calendar"]["views"]["summary"]["meaning"]
    assert llm_input.dictionary["payment_calendar_view"] == [
        "summary",
        "details",
        "payments",
        "income",
        "balance_start",
        "balance_end",
    ]
    assert "реклама" in llm_input.dictionary["report_rules"]["payment_calendar"]["filters"]["article"]["examples"]
    assert llm_input.dictionary["project"] == ["obvodny", "moskovsky", "evgenievsky", "all"]
