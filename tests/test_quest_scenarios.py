from dataclasses import dataclass
from typing import Any

from app.calculation_engine import calculate_operation
from app.context_resolver import resolve_context
from app.llm_parser import LLMParsedResponse
from app.metric_resolver import resolve_metrics
from app.query_frame import build_query_frame
from app.sql_compiler import compile_sql


@dataclass(frozen=True)
class QuestScenario:
    user_request: str
    llm_payload: dict[str, Any]
    expected_report_type: str
    expected_project: str
    expected_metrics: list[str]
    expected_group_by: list[str]
    expected_table: str


def build_pipeline(payload: dict[str, Any], current_state: dict[str, Any] | None = None):
    parsed = LLMParsedResponse.model_validate(payload)
    state = resolve_context(current_state or {}, parsed)
    frame = build_query_frame(state)
    metric_resolution = resolve_metrics(frame)
    return state, frame, metric_resolution


def test_quest_data_scenarios_compile_to_sql() -> None:
    scenarios = [
        QuestScenario(
            user_request="Обводный сумма выручки за все время",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "sales_report",
                    "project": "obvodny_118",
                    "metrics": ["revenue"],
                },
                "confidence": 0.9,
            },
            expected_report_type="sales_report",
            expected_project="obvodny_118",
            expected_metrics=["revenue"],
            expected_group_by=[],
            expected_table="sales_facts",
        ),
        QuestScenario(
            user_request="Сколько квадратных метров было продано в марте 2026 по проекту велл",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "sales_report",
                    "project": "well_moskovsky",
                    "period": {
                        "from": "2026-03-01",
                        "to": "2026-03-31",
                        "label": "март 2026",
                    },
                    "metrics": ["sold_area"],
                },
                "confidence": 0.9,
            },
            expected_report_type="sales_report",
            expected_project="well_moskovsky",
            expected_metrics=["sold_area"],
            expected_group_by=[],
            expected_table="sales_facts",
        ),
        QuestScenario(
            user_request="Дай эту информацию в разбивке по типам помещений",
            llm_payload={
                "intent": "context_query",
                "state_delta": {
                    "group_by": ["room_type"],
                },
                "confidence": 0.9,
            },
            expected_report_type="sales_report",
            expected_project="well_moskovsky",
            expected_metrics=["sold_area"],
            expected_group_by=["room_type"],
            expected_table="sales_facts",
        ),
        QuestScenario(
            user_request="Платежный календарь за март 2026 года какие отклонения и общую сумму",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "payment_calendar",
                    "project": "all",
                    "period": {
                        "from": "2026-03-01",
                        "to": "2026-03-31",
                        "label": "март 2026",
                    },
                    "metrics": ["deviation"],
                    "group_by": ["metric"],
                },
                "confidence": 0.9,
            },
            expected_report_type="payment_calendar",
            expected_project="all",
            expected_metrics=["deviation"],
            expected_group_by=["metric"],
            expected_table="payment_calendar_facts",
        ),
        QuestScenario(
            user_request="Сколько сделок с ВТБ",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "sales_report",
                    "project": "all",
                    "metrics": ["deal_count"],
                    "filters": {"bank": "vtb"},
                },
                "confidence": 0.9,
            },
            expected_report_type="sales_report",
            expected_project="all",
            expected_metrics=["deal_count"],
            expected_group_by=[],
            expected_table="sales_facts",
        ),
    ]
    current_state = {
        "report_type": "sales_report",
        "project": "well_moskovsky",
        "period": {
            "from": "2026-03-01",
            "to": "2026-03-31",
            "label": "март 2026",
        },
        "metrics": ["sold_area"],
    }

    for scenario in scenarios:
        state_seed = current_state if scenario.llm_payload["intent"] == "context_query" else None
        _, frame, metric_resolution = build_pipeline(scenario.llm_payload, state_seed)
        sql_query = compile_sql(frame, metric_resolution)

        assert frame.ready is True, scenario.user_request
        assert metric_resolution.valid is True, scenario.user_request
        assert frame.report_type == scenario.expected_report_type
        assert frame.project == scenario.expected_project
        assert frame.metrics == scenario.expected_metrics
        assert frame.group_by == scenario.expected_group_by
        assert sql_query.table == scenario.expected_table


def test_quest_math_scenario_uses_last_result() -> None:
    _, frame, metric_resolution = build_pipeline(
        {
            "intent": "math_on_last_result",
            "state_delta": {},
            "operation": {
                "type": "divide",
                "left": {
                    "source": "last_result",
                    "metric": "revenue",
                },
                "right": {
                    "source": "literal",
                    "value": 2,
                },
            },
            "confidence": 0.9,
        },
        {
            "report_type": "sales_report",
            "project": "obvodny_118",
            "metrics": ["revenue"],
        },
    )

    calculation_result = calculate_operation(
        frame.operation or {},
        {
            "rows": [
                {
                    "revenue": 100,
                },
            ],
        },
    )

    assert frame.ready is True
    assert metric_resolution.valid is True
    assert calculation_result.rows == [{"value": 50.0}]
