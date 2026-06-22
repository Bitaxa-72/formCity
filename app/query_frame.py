from typing import Any

from pydantic import BaseModel, Field

from app.llm_dictionary import Intent


DEFAULT_REPORT_TYPE = "summary"
DEFAULT_PROJECT = "all"
DEFAULT_PERIOD_LABEL = "весь доступный период"


class QueryPeriod(BaseModel):
    from_date: str | None = Field(default=None, alias="from")
    to: str | None = None
    label: str | None = None


class QueryFrame(BaseModel):
    intent: str | None
    report_type: str | None
    project: str | None
    period: QueryPeriod
    metrics: list[str]
    filters: dict[str, Any]
    group_by: list[str]
    operation: dict[str, Any] | None = None
    ready: bool
    missing_fields: list[str]
    clarification_question: str | None = None


def apply_query_defaults(state: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(state)
    prepared["report_type"] = prepared.get("report_type") or DEFAULT_REPORT_TYPE
    prepared["project"] = prepared.get("project") or DEFAULT_PROJECT

    period = dict(prepared.get("period") or {})
    if not period.get("from") and not period.get("to"):
        period["label"] = period.get("label") or DEFAULT_PERIOD_LABEL
    prepared["period"] = period
    return prepared


def find_missing_fields(state: dict[str, Any]) -> list[str]:
    missing = []
    if not state.get("metrics") and not state.get("pending_operation"):
        missing.append("metrics")
    return missing


def build_clarification_question(missing_fields: list[str]) -> str | None:
    if not missing_fields:
        return None

    labels = {
        "metrics": "метрику",
        "project": "проект",
        "period": "период",
    }
    missing_labels = [labels.get(field, field) for field in missing_fields]
    return "Уточните " + " и ".join(missing_labels) + " для запроса."


def build_query_frame(state: dict[str, Any]) -> QueryFrame:
    prepared = apply_query_defaults(state)
    intent = prepared.get("last_intent")
    operation = prepared.get("pending_operation")

    if intent == Intent.MATH_ON_LAST_RESULT.value:
        missing_fields = [] if operation else ["operation"]
    elif intent in {Intent.GENERAL_QUESTION.value, Intent.UNSUPPORTED.value}:
        missing_fields = []
    else:
        missing_fields = find_missing_fields(prepared)

    ready = not missing_fields and not prepared.get("awaiting_clarification")

    return QueryFrame(
        intent=intent,
        report_type=prepared.get("report_type"),
        project=prepared.get("project"),
        period=QueryPeriod.model_validate(prepared.get("period") or {}),
        metrics=prepared.get("metrics") or [],
        filters=prepared.get("filters") or {},
        group_by=prepared.get("group_by") or [],
        operation=operation,
        ready=ready,
        missing_fields=missing_fields,
        clarification_question=prepared.get("clarification_target") or build_clarification_question(missing_fields),
    )
