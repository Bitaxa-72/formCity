from dataclasses import dataclass
from typing import Any

from app.llm.parser import LLMParsedResponse
from app.pipeline.calculation_engine import calculate_operation
from app.pipeline.context_resolver import resolve_context
from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics
from app.pipeline.sql_compiler import compile_sql


@dataclass(frozen=True)
class QuestScenario:
    user_request: str
    llm_payload: dict[str, Any]
    expected_project: str
    expected_metrics: list[str]
    expected_group_by: list[str]


def build_pipeline(payload: dict[str, Any], current_state: dict[str, Any] | None = None):
    parsed = LLMParsedResponse.model_validate(payload)
    state = resolve_context(current_state or {}, parsed)
    frame = apply_report_semantics(build_query_frame(state))
    metric_resolution = resolve_metrics(frame)
    return state, frame, metric_resolution


def test_quest_data_scenarios_compile_to_sql() -> None:
    scenarios = [
        QuestScenario(
            user_request="Платежи обводный март факт",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "payment_calendar",
                    "project": "obvodny",
                    "period": {
                        "from": "2026-03-01",
                        "to": "2026-03-31",
                        "label": "март 2026",
                    },
                    "metrics": ["fact"],
                    "filters": {"article_kind": "payment_total"},
                },
                "confidence": 0.9,
            },
            expected_project="obvodny",
            expected_metrics=["fact"],
            expected_group_by=[],
        ),
        QuestScenario(
            user_request="Дай план и факт по платежам московский апрель",
            llm_payload={
                "intent": "data_query",
                "state_delta": {
                    "report_type": "payment_calendar",
                    "project": "moskovsky",
                    "period": {
                        "from": "2026-04-01",
                        "to": "2026-04-30",
                        "label": "апрель 2026",
                    },
                    "metrics": ["plan", "fact"],
                    "filters": {"article_kind": "payment_total"},
                },
                "confidence": 0.9,
            },
            expected_project="moskovsky",
            expected_metrics=["plan", "fact"],
            expected_group_by=[],
        ),
        QuestScenario(
            user_request="Покажи в разбивке по статьям",
            llm_payload={
                "intent": "context_query",
                "state_delta": {
                    "filters": {"article_kind": "detail"},
                    "group_by": ["metric"],
                },
                "confidence": 0.9,
            },
            expected_project="moskovsky",
            expected_metrics=["plan", "fact"],
            expected_group_by=["metric"],
        ),
    ]
    current_state = {
        "report_type": "payment_calendar",
        "project": "moskovsky",
        "period": {
            "from": "2026-04-01",
            "to": "2026-04-30",
            "label": "апрель 2026",
        },
        "metrics": ["plan", "fact"],
        "filters": {"article_kind": "payment_total"},
    }

    for scenario in scenarios:
        state_seed = current_state if scenario.llm_payload["intent"] == "context_query" else None
        _, frame, metric_resolution = build_pipeline(scenario.llm_payload, state_seed)
        sql_query = compile_sql(frame, metric_resolution)

        assert frame.ready is True, scenario.user_request
        assert metric_resolution.valid is True, scenario.user_request
        assert frame.report_type == "payment_calendar"
        assert frame.project == scenario.expected_project
        assert frame.metrics == scenario.expected_metrics
        assert frame.group_by == scenario.expected_group_by
        assert sql_query.table == "payment_calendar_facts"


def test_quest_math_scenario_uses_last_result() -> None:
    _, frame, metric_resolution = build_pipeline(
        {
            "intent": "math_on_last_result",
            "state_delta": {},
            "operation": {
                "type": "divide",
                "left": {
                    "source": "last_result",
                    "metric": "fact",
                },
                "right": {
                    "source": "literal",
                    "value": 2,
                },
            },
            "confidence": 0.9,
        },
        {
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
        },
    )

    calculation_result = calculate_operation(
        frame.operation or {},
        {
            "rows": [
                {
                    "fact": 100,
                },
            ],
        },
    )

    assert frame.ready is True
    assert metric_resolution.valid is True
    assert calculation_result.rows == [{"value": 50.0}]
