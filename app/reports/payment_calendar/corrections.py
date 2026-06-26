from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    clear_failed_query_markers,
)
from app.reports.payment_calendar.compatibility import PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES


def resolve_payment_calendar_group_by_correction(text: str | None) -> str | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    markers = {
        "project": ("проект", "проет", "объект"),
        "article": ("стат",),
        "article_kind": ("раздел", "поступ", "платеж", "остат", "расход"),
        "month": ("период", "месяц", "дат"),
    }
    for group_by, aliases in markers.items():
        if any(alias in normalized_text for alias in aliases):
            return group_by
    return None


def resolve_payment_calendar_metric_or_view_correction(text: str | None) -> dict[str, object] | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    metric_markers: dict[str, tuple[str, ...]] = {
        "plan": ("план", "планов"),
        "fact": ("факт", "фактичес"),
        "deviation": ("отклон", "разниц"),
    }
    for metric, aliases in metric_markers.items():
        if any(alias in normalized_text for alias in aliases):
            return {"metrics": [metric], "view": None, "filters": None}

    view_markers: dict[str, tuple[str, ...]] = {
        "summary": ("итог", "свод"),
        "income": ("поступ",),
        "payments": ("платеж", "расход"),
        "balance_start": ("остаток на начал", "начал"),
        "balance_end": ("остаток на конец", "конец"),
        "details": ("стать", "детал", "подроб"),
    }
    for view, aliases in view_markers.items():
        if any(alias in normalized_text for alias in aliases):
            return {"metrics": ["plan", "fact", "deviation"], "view": view, "filters": {}}
    return None


def remove_unsupported_metric_article_filter(filters: object) -> dict[str, object]:
    if not isinstance(filters, dict):
        return {}

    cleaned = dict(filters)
    article = cleaned.get("article")
    if isinstance(article, str):
        normalized_article = normalize_search_text(article)
        unsupported_terms = set(PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES)
        unsupported_terms.update(PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES.values())
        if normalized_article in unsupported_terms:
            cleaned.pop("article", None)
    return cleaned


def build_failed_group_by_correction(
    state: dict[str, object] | None,
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse] | None:
    if not state or state.get(CONTEXT_BLOCKED_AFTER_ERROR) is not True:
        return None
    if state.get(FAILED_QUERY_ERROR) != "group_by_not_supported_for_payment_calendar":
        return None

    failed_state = state.get(FAILED_QUERY_STATE)
    if not isinstance(failed_state, dict):
        return None

    group_by = resolve_payment_calendar_group_by_correction(text)
    if group_by is None:
        return None

    corrected_state = dict(failed_state)
    corrected_state["group_by"] = [group_by]
    if group_by == "project":
        corrected_state["project"] = "all"
    corrected_state["awaiting_clarification"] = False
    corrected_state["clarification_target"] = None
    corrected_state["clarification_base_state"] = None
    corrected_state["clarification_kind"] = None
    corrected_state["clarification_options"] = []
    corrected_state = clear_failed_query_markers(corrected_state)

    delta_data: dict[str, object] = {"group_by": [group_by]}
    if corrected_state.get("metrics"):
        delta_data["metrics"] = corrected_state["metrics"]
    if group_by == "project":
        delta_data["project"] = "all"
    parsed_response = LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(delta_data),
        confidence=1,
    )
    return corrected_state, parsed_response


def build_failed_metric_correction(
    state: dict[str, object] | None,
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse] | None:
    if not state or state.get(CONTEXT_BLOCKED_AFTER_ERROR) is not True:
        return None
    if state.get(FAILED_QUERY_ERROR) != "metric_not_supported_for_payment_calendar":
        return None

    failed_state = state.get(FAILED_QUERY_STATE)
    if not isinstance(failed_state, dict):
        return None

    correction = resolve_payment_calendar_metric_or_view_correction(text)
    if correction is None:
        return None

    corrected_state = dict(failed_state)
    corrected_state["metrics"] = correction["metrics"]
    corrected_state["view"] = correction["view"]
    if correction["filters"] is not None:
        corrected_state["filters"] = correction["filters"]
    else:
        corrected_state["filters"] = remove_unsupported_metric_article_filter(corrected_state.get("filters"))
    corrected_state["group_by"] = []
    corrected_state["awaiting_clarification"] = False
    corrected_state["clarification_target"] = None
    corrected_state["clarification_base_state"] = None
    corrected_state["clarification_kind"] = None
    corrected_state["clarification_options"] = []
    corrected_state = clear_failed_query_markers(corrected_state)

    delta_data: dict[str, object] = {"metrics": correction["metrics"], "group_by": []}
    if correction["view"] is not None:
        delta_data["view"] = correction["view"]
    if correction["filters"] is not None:
        delta_data["filters"] = correction["filters"]
    parsed_response = LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(delta_data),
        confidence=1,
    )
    return corrected_state, parsed_response
