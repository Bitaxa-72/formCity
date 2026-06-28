from app.llm.dictionary import REPORT_TYPE_ALIASES
from app.pipeline.domain_resolver import normalize_search_text


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


def build_failed_query_state(
    current_state: dict[str, object],
    resolved_state: dict[str, object],
    error: str | None,
) -> dict[str, object]:
    if error == "metric_not_supported_for_payment_calendar":
        return clear_failed_query_markers(dict(current_state))
    return clear_failed_query_markers(dict(resolved_state))
