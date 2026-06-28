from app.llm.dictionary import REPORT_TYPE_ALIASES
from app.pipeline.domain_resolver import normalize_search_text
from app.reports.payment_calendar.compatibility import PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES


CONTEXT_BLOCKED_AFTER_ERROR = "context_blocked_after_error"
FAILED_QUERY_ERROR = "failed_query_error"
FAILED_QUERY_STATE = "failed_query_state"
CONTEXT_BLOCKED_MESSAGE = (
    "Предыдущий запрос не был выполнен, поэтому короткое уточнение не к чему применить.\n\n"
    "Сформулируйте новый запрос полностью: тип отчета, проект, показатель и период."
)


def text_mentions_report_type(text: str | None) -> bool:
    normalized_text = normalize_search_text(text)
    if not normalized_text:
        return False

    for aliases in REPORT_TYPE_ALIASES.values():
        for alias in aliases:
            if normalize_search_text(alias) in normalized_text:
                return True
    return False


def block_short_followup_after_error(state: dict[str, object] | None, text: str | None) -> bool:
    return bool(state and state.get(CONTEXT_BLOCKED_AFTER_ERROR) is True and not text_mentions_report_type(text))


def clear_failed_query_markers(state: dict[str, object]) -> dict[str, object]:
    cleaned = dict(state)
    cleaned.pop(CONTEXT_BLOCKED_AFTER_ERROR, None)
    cleaned.pop(FAILED_QUERY_ERROR, None)
    cleaned.pop(FAILED_QUERY_STATE, None)
    return cleaned


def is_payment_calendar_unsupported_metric_value(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized_value = normalize_search_text(value)
    unsupported_terms = {
        normalize_search_text(term)
        for term in (
            *PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES.keys(),
            *PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES.values(),
        )
    }
    return normalized_value in unsupported_terms


def build_payment_calendar_failed_metric_state(
    current_state: dict[str, object],
    resolved_state: dict[str, object],
) -> dict[str, object]:
    failed_state = dict(resolved_state)
    filters = failed_state.get("filters")
    if not isinstance(filters, dict):
        return clear_failed_query_markers(failed_state)

    article = filters.get("article")
    if not is_payment_calendar_unsupported_metric_value(article):
        return clear_failed_query_markers(failed_state)

    current_filters = current_state.get("filters")
    current_article = current_filters.get("article") if isinstance(current_filters, dict) else None
    cleaned_filters = dict(filters)
    if isinstance(current_article, str) and not is_payment_calendar_unsupported_metric_value(current_article):
        cleaned_filters["article"] = current_article
    else:
        cleaned_filters.pop("article", None)
    failed_state["filters"] = cleaned_filters
    return clear_failed_query_markers(failed_state)


def build_failed_query_state(
    current_state: dict[str, object],
    resolved_state: dict[str, object],
    error: str | None,
) -> dict[str, object]:
    if error == "metric_not_supported_for_payment_calendar":
        return build_payment_calendar_failed_metric_state(current_state, resolved_state)
    return clear_failed_query_markers(dict(resolved_state))
