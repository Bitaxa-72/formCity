from typing import Any

from pydantic import BaseModel, Field

from app.llm.dictionary import Intent


DEFAULT_PROJECT = "all"
DEFAULT_PERIOD_LABEL = "весь доступный период"
NON_DATA_QUERY_MESSAGE = (
    "Не понял запрос к данным.\n\n"
    "Укажите, пожалуйста, тип отчета, проект, метрику и период.\n\n"
    "Доступные отчеты:\n"
    "- сводный отчет\n"
    "- модель\n"
    "- платежный календарь\n"
    "- дорожная карта\n"
    "- отчет о продажах\n"
    "- отчет об исполнении плана продаж\n"
    "- отчет по агентам\n"
    "- остатки в продаже\n"
    "- ДЗ и брони\n"
    "- непроектные расходы"
)
REPORT_TYPE_CLARIFICATION = (
    "Я должен понимать, какой тип отчета вас интересует, чтобы верно достать информацию.\n\n"
    "Доступные типы отчетов:\n"
    "- сводный отчет\n"
    "- модель\n"
    "- платежный календарь\n"
    "- дорожная карта\n"
    "- отчет о продажах\n"
    "- отчет об исполнении плана продаж\n"
    "- отчет по агентам\n"
    "- остатки в продаже\n"
    "- ДЗ и брони\n"
    "- непроектные расходы\n\n"
    "Уточните, пожалуйста, по какому отчету нужен расчет?"
)
DIMENSION_CLARIFICATION = (
    "Что показать в платежном календаре?\n\n"
    "Можно запросить:\n"
    "- статьи\n"
    "- статьи расходов\n"
    "- проекты\n"
    "- периоды\n"
    "- типы строк"
)


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
    view: str | None = None
    dimension: str | None = None
    filters: dict[str, Any]
    group_by: list[str]
    operation: dict[str, Any] | None = None
    ready: bool
    missing_fields: list[str]
    clarification_question: str | None = None


def apply_query_defaults(state: dict[str, Any]) -> dict[str, Any]:
    prepared = dict(state)
    prepared["project"] = prepared.get("project") or DEFAULT_PROJECT

    period = dict(prepared.get("period") or {})
    if not period.get("from") and not period.get("to"):
        period["label"] = period.get("label") or DEFAULT_PERIOD_LABEL
    prepared["period"] = period

    group_by = list(prepared.get("group_by") or [])
    if prepared["project"] == DEFAULT_PROJECT and prepared.get("metrics") and prepared.get("last_intent") != Intent.DIMENSION_QUERY.value:
        if "project" not in group_by:
            group_by.insert(0, "project")
    prepared["group_by"] = group_by
    return prepared


def find_missing_fields(state: dict[str, Any]) -> list[str]:
    missing = []
    if not state.get("report_type"):
        missing.append("report_type")
    if state.get("last_intent") == Intent.DIMENSION_QUERY.value:
        if not state.get("dimension"):
            missing.append("dimension")
    elif not state.get("metrics") and not state.get("pending_operation") and not state.get("view"):
        missing.append("metrics")
    return missing


def build_clarification_question(missing_fields: list[str]) -> str | None:
    if not missing_fields:
        return None
    if "report_type" in missing_fields:
        return REPORT_TYPE_CLARIFICATION
    if "dimension" in missing_fields:
        return DIMENSION_CLARIFICATION

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
        missing_fields = ["intent"]
    else:
        missing_fields = find_missing_fields(prepared)

    ready = not missing_fields and not prepared.get("awaiting_clarification")

    if intent in {Intent.GENERAL_QUESTION.value, Intent.UNSUPPORTED.value}:
        clarification_question = NON_DATA_QUERY_MESSAGE
    else:
        clarification_question = build_clarification_question(missing_fields) if missing_fields else prepared.get("clarification_target")

    return QueryFrame(
        intent=intent,
        report_type=prepared.get("report_type"),
        project=prepared.get("project"),
        period=QueryPeriod.model_validate(prepared.get("period") or {}),
        metrics=prepared.get("metrics") or [],
        view=prepared.get("view"),
        dimension=prepared.get("dimension"),
        filters=prepared.get("filters") or {},
        group_by=prepared.get("group_by") or [],
        operation=operation,
        ready=ready,
        missing_fields=missing_fields,
        clarification_question=clarification_question,
    )
