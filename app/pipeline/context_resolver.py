from copy import deepcopy
from typing import Any

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.reports.payment_calendar.catalog import PAYMENT_CALENDAR_FULL_METRICS
from app.reports.registry import METRIC_CATALOG, SQL_TEMPLATES


DEFAULT_DIALOG_STATE: dict[str, Any] = {
    "report_type": None,
    "project": None,
    "period": {
        "from": None,
        "to": None,
        "label": None,
    },
    "metrics": [],
    "view": None,
    "dimension": None,
    "filters": {},
    "group_by": [],
    "sort": None,
    "limit": None,
    "last_intent": None,
    "awaiting_clarification": False,
    "clarification_target": None,
    "clarification_base_state": None,
    "clarification_kind": None,
    "clarification_options": [],
}


def empty_dialog_state() -> dict[str, Any]:
    return deepcopy(DEFAULT_DIALOG_STATE)


def normalize_state(state: dict[str, Any] | None) -> dict[str, Any]:
    normalized = empty_dialog_state()
    for key, value in (state or {}).items():
        if key == "period" and isinstance(value, dict):
            normalized["period"].update(value)
        elif key == "filters" and isinstance(value, dict):
            normalized["filters"].update(value)
        elif key in normalized:
            normalized[key] = value
    return normalized


def apply_period_delta(period: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    if value.get("mode") == "all":
        return {
            "from": None,
            "to": None,
            "label": "весь доступный период",
        }

    updated_period = deepcopy(period)
    updated_period.update({key: item for key, item in value.items() if key != "mode"})
    return updated_period


def apply_state_delta(state: dict[str, Any], delta: StateDelta) -> dict[str, Any]:
    updated = deepcopy(state)
    delta_data = delta.model_dump(mode="json", by_alias=True, exclude_none=True)

    for key, value in delta_data.items():
        if key == "period":
            updated["period"] = apply_period_delta(updated["period"], value)
        elif key == "filters":
            updated["filters"].update(value)
        else:
            updated[key] = value

    return updated


def reset_fields(state: dict[str, Any], fields: set[str], protected_fields: set[str]) -> None:
    defaults = empty_dialog_state()
    for field in fields - protected_fields:
        state[field] = deepcopy(defaults[field])


def reconcile_state_tree(
    previous_state: dict[str, Any],
    updated_state: dict[str, Any],
    delta: StateDelta,
    *,
    reset_on_report_type_change: bool = True,
) -> dict[str, Any]:
    reconciled = deepcopy(updated_state)
    delta_data = delta.model_dump(mode="json", by_alias=True, exclude_none=True)
    changed_fields = set(delta_data)

    if reset_on_report_type_change and "report_type" in changed_fields and delta_data["report_type"] != previous_state.get("report_type"):
        reset_fields(
            reconciled,
            {"period", "metrics", "view", "dimension", "filters", "group_by", "sort", "limit"},
            changed_fields,
        )

    if "view" in changed_fields:
        reset_fields(reconciled, {"dimension", "filters", "group_by"}, changed_fields)

    if "dimension" in changed_fields:
        reset_fields(reconciled, {"metrics", "view", "group_by"}, changed_fields)

    if "metrics" in changed_fields:
        reset_fields(reconciled, {"dimension", "view"}, changed_fields)

    if reconciled.get("report_type") == "sales_report" and "period" in changed_fields and "filters" not in changed_fields:
        filters = dict(reconciled.get("filters") or {})
        filters.pop("period_month", None)
        if filters.get("period_kind") == "month":
            filters.pop("period_kind", None)
        reconciled["filters"] = filters

    return reconciled


def has_existing_period(state: dict[str, Any]) -> bool:
    period = state.get("period") or {}
    return bool(period.get("from") or period.get("to") or period.get("label"))


def prepare_clarification_delta(previous_state: dict[str, Any], delta: StateDelta) -> StateDelta:
    delta_data = delta.model_dump(mode="json", by_alias=True, exclude_none=True)
    period = delta_data.get("period")
    if isinstance(period, dict) and period.get("mode") == "all" and has_existing_period(previous_state):
        delta_data.pop("period", None)
        return StateDelta.model_validate(delta_data)
    return delta


def delta_data(delta: StateDelta) -> dict[str, Any]:
    return delta.model_dump(mode="json", by_alias=True, exclude_none=True)


def delta_has_report_type(delta: StateDelta) -> bool:
    return "report_type" in delta_data(delta)


def delta_has_metrics(delta: StateDelta) -> bool:
    return "metrics" in delta_data(delta)


def delta_changes_scope(delta: StateDelta) -> bool:
    data = delta_data(delta)
    if "project" in data or "period" in data:
        return True
    filters = data.get("filters")
    return isinstance(filters, dict) and bool(filters)


def delta_is_compatible_with_report(report_type: str | None, delta: StateDelta) -> bool:
    if not report_type:
        return True

    data = delta_data(delta)
    metric_catalog = METRIC_CATALOG.get(report_type, {})
    sql_template = SQL_TEMPLATES.get(report_type)
    if sql_template is None:
        return True

    metrics = data.get("metrics")
    if isinstance(metrics, list) and any(metric not in metric_catalog for metric in metrics):
        return False

    filters = data.get("filters")
    if isinstance(filters, dict) and any(key not in sql_template.filter_columns for key in filters):
        return False

    group_by = data.get("group_by")
    if isinstance(group_by, list) and any(key not in sql_template.group_by_columns for key in group_by):
        return False

    dimension = data.get("dimension")
    if isinstance(dimension, str) and dimension not in sql_template.dimension_columns:
        return False

    return True


def should_start_new_state(
    current_state: dict[str, Any],
    parsed_response: LLMParsedResponse,
    is_clarification_mode: bool,
) -> bool:
    if is_clarification_mode:
        return False
    if parsed_response.intent not in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY}:
        return False
    if delta_has_report_type(parsed_response.state_delta):
        return True
    return not bool(current_state.get("report_type"))


def should_discard_incompatible_report_context(
    current_state: dict[str, Any],
    parsed_response: LLMParsedResponse,
    is_clarification_mode: bool,
) -> bool:
    if is_clarification_mode:
        return False
    if parsed_response.intent not in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY, Intent.CONTEXT_QUERY}:
        return False
    if delta_has_report_type(parsed_response.state_delta):
        return False
    if not current_state.get("report_type"):
        return False
    return not delta_is_compatible_with_report(current_state.get("report_type"), parsed_response.state_delta)


def is_report_type_clarification_answer(current_state: dict[str, Any], parsed_response: LLMParsedResponse) -> bool:
    if current_state.get("clarification_kind") != "report_type":
        return False
    data = delta_data(parsed_response.state_delta)
    return set(data) == {"report_type"}


def is_new_query_during_clarification(current_state: dict[str, Any], parsed_response: LLMParsedResponse) -> bool:
    if parsed_response.intent not in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY, Intent.CONTEXT_QUERY}:
        return False

    if is_report_type_clarification_answer(current_state, parsed_response):
        return False

    data = delta_data(parsed_response.state_delta)
    if "report_type" in data or "view" in data or "dimension" in data or "group_by" in data:
        return True
    return False


def build_clarification_base_state(state: dict[str, Any]) -> dict[str, Any]:
    base_state = normalize_state(state)
    base_state["awaiting_clarification"] = False
    base_state["clarification_target"] = None
    base_state["clarification_base_state"] = None
    base_state["clarification_kind"] = None
    base_state["clarification_options"] = []
    return base_state


def set_clarification_state(
    state: dict[str, Any],
    question: str | None,
    *,
    kind: str | None = None,
    options: list[str] | None = None,
) -> dict[str, Any]:
    updated = deepcopy(state)
    updated["awaiting_clarification"] = True
    updated["clarification_target"] = question
    updated["clarification_base_state"] = build_clarification_base_state(state)
    updated["clarification_kind"] = kind
    updated["clarification_options"] = options or []
    return updated


def apply_partial_query_defaults(
    resolved: dict[str, Any],
    parsed_response: LLMParsedResponse,
    starts_new_state: bool,
    is_clarification_mode: bool,
) -> dict[str, Any]:
    if is_clarification_mode:
        return resolved
    if parsed_response.intent != Intent.DATA_QUERY:
        return resolved
    if delta_has_metrics(parsed_response.state_delta):
        return resolved
    if resolved.get("report_type") != "payment_calendar":
        return resolved

    data = delta_data(parsed_response.state_delta)
    filters = data.get("filters")
    has_concrete_filter = isinstance(filters, dict) and bool(filters)
    if starts_new_state and not has_concrete_filter:
        return resolved
    if not starts_new_state and not delta_changes_scope(parsed_response.state_delta):
        return resolved

    updated = deepcopy(resolved)
    updated["metrics"] = PAYMENT_CALENDAR_FULL_METRICS.copy()
    updated["dimension"] = None
    return updated


def clear_article_filter_for_article_wide_query(resolved: dict[str, Any], delta: StateDelta) -> dict[str, Any]:
    data = delta_data(delta)
    is_article_dimension = data.get("dimension") == "article"
    group_by = data.get("group_by")
    is_article_grouping = isinstance(group_by, list) and "article" in group_by
    if not is_article_dimension and not is_article_grouping:
        return resolved

    filters = dict(resolved.get("filters") or {})
    filters.pop("article", None)
    updated = deepcopy(resolved)
    updated["filters"] = filters
    return updated


def resolve_context(
    current_state: dict[str, Any] | None,
    parsed_response: LLMParsedResponse,
) -> dict[str, Any]:
    normalized_current_state = normalize_state(current_state)
    is_clarification_mode = bool(normalized_current_state.get("awaiting_clarification"))
    if is_clarification_mode and is_new_query_during_clarification(normalized_current_state, parsed_response):
        is_clarification_mode = False

    effective_intent = parsed_response.intent
    if is_clarification_mode and parsed_response.intent in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY}:
        if parsed_response.intent == Intent.DIMENSION_QUERY and parsed_response.state_delta.dimension:
            effective_intent = Intent.DIMENSION_QUERY
        else:
            effective_intent = Intent.CLARIFICATION_ANSWER

    discard_incompatible_report_context = should_discard_incompatible_report_context(
        normalized_current_state,
        parsed_response,
        is_clarification_mode,
    )
    starts_new_state = discard_incompatible_report_context or should_start_new_state(
        normalized_current_state,
        parsed_response,
        is_clarification_mode,
    )
    if starts_new_state:
        previous_state = empty_dialog_state()
        resolved = empty_dialog_state()
    else:
        base_state = normalized_current_state.get("clarification_base_state")
        previous_state = normalize_state(base_state) if is_clarification_mode and isinstance(base_state, dict) else normalized_current_state
        resolved = previous_state

    state_delta = (
        prepare_clarification_delta(previous_state, parsed_response.state_delta)
        if is_clarification_mode
        else parsed_response.state_delta
    )
    resolved = apply_state_delta(resolved, state_delta)
    resolved = reconcile_state_tree(
        previous_state,
        resolved,
        state_delta,
        reset_on_report_type_change=effective_intent != Intent.CLARIFICATION_ANSWER,
    )
    resolved = apply_partial_query_defaults(
        resolved,
        parsed_response,
        starts_new_state,
        is_clarification_mode,
    )
    resolved = clear_article_filter_for_article_wide_query(resolved, state_delta)
    resolved["last_intent"] = effective_intent.value
    resolved["awaiting_clarification"] = parsed_response.needs_clarification
    resolved["clarification_target"] = parsed_response.clarification_question if parsed_response.needs_clarification else None
    if parsed_response.needs_clarification:
        resolved["clarification_base_state"] = build_clarification_base_state(resolved)
    else:
        resolved["clarification_base_state"] = None
        resolved["clarification_kind"] = None
        resolved["clarification_options"] = []

    if effective_intent == Intent.MATH_ON_LAST_RESULT and parsed_response.operation:
        resolved["pending_operation"] = parsed_response.operation.model_dump(mode="json")
    else:
        resolved.pop("pending_operation", None)

    return resolved
