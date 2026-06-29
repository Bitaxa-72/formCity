import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    clear_failed_query_markers,
)
from app.reports.payment_calendar.compatibility import (
    PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES,
    find_payment_calendar_unsupported_metric,
)


PAYMENT_CALENDAR_REPORT_MARKERS = ("платежный календар", "платежному календар", "платежном календар")
PAYMENT_CALENDAR_UNSUPPORTED_GROUP_BY_MARKERS = {
    "floor": ("по этаж", "этажам", "этажи"),
    "room_type": ("по типам помещ", "типам помещ", "помещениям"),
    "agent": ("по агент", "агентам"),
    "bank": ("по банк", "банкам"),
}
PAYMENT_CALENDAR_GROUP_BY_ARTICLE_EXCLUSIONS = (
    "проект",
    "проектам",
    "период",
    "периодам",
    "месяц",
    "месяцам",
    "статьям",
    "всем стать",
    "раздел",
    "разделам",
    "этаж",
    "этажам",
    "типам помещ",
    "помещениям",
    "агент",
    "агентам",
    "банк",
    "банкам",
)
PAYMENT_CALENDAR_PROJECT_MARKERS = {
    "moskovsky": ("московск",),
    "obvodny": ("обводн",),
    "evgenievsky": ("евгеньевск", "евген",),
}
PAYMENT_CALENDAR_MONTHS = (
    "январь",
    "января",
    "февраль",
    "февраля",
    "март",
    "марта",
    "апрель",
    "апреля",
    "май",
    "мая",
    "июнь",
    "июня",
    "июль",
    "июля",
    "август",
    "августа",
    "сентябрь",
    "сентября",
    "октябрь",
    "октября",
    "ноябрь",
    "ноября",
    "декабрь",
    "декабря",
)


def resolve_payment_calendar_project(text: str | None) -> str | None:
    normalized_text = normalize_search_text(text or "")
    for project, aliases in PAYMENT_CALENDAR_PROJECT_MARKERS.items():
        if any(alias in normalized_text for alias in aliases):
            return project
    return None


def resolve_payment_calendar_period_label(text: str | None) -> str | None:
    normalized_text = normalize_search_text(text or "")
    for month in PAYMENT_CALENDAR_MONTHS:
        if month in normalized_text.split():
            return month
    return None


def resolve_payment_calendar_metric(text: str | None) -> list[str]:
    normalized_text = normalize_search_text(text or "")
    metrics = []
    if "план" in normalized_text:
        metrics.append("plan")
    if "факт" in normalized_text:
        metrics.append("fact")
    if "отклон" in normalized_text or "разниц" in normalized_text:
        metrics.append("deviation")
    if metrics:
        return metrics
    return ["plan", "fact", "deviation"]


def has_payment_calendar_metric_marker(text: str | None) -> bool:
    normalized_text = normalize_search_text(text or "")
    return any(marker in normalized_text for marker in ("план", "факт", "отклон", "разниц"))


def resolve_payment_calendar_unsupported_group_by(text: str | None) -> str | None:
    normalized_text = normalize_search_text(text or "")
    for group_by, markers in PAYMENT_CALENDAR_UNSUPPORTED_GROUP_BY_MARKERS.items():
        if any(marker in normalized_text for marker in markers):
            return group_by
    return None


def extract_payment_calendar_article_filter(text: str | None) -> str | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    for match in re.finditer(r"(?:^|\s)по\s+(.+?)(?=\s+за\s+|\s+с\s+|\s+на\s+|$)", normalized_text):
        candidate = match.group(1).strip(" ,.;:")
        if not candidate:
            continue
        if any(candidate == marker or candidate.startswith(f"{marker} ") for marker in PAYMENT_CALENDAR_GROUP_BY_ARTICLE_EXCLUSIONS):
            continue
        return candidate
    return None


def build_article_filter_request_correction(
    text: str | None,
    *,
    payment_calendar_context: bool = False,
) -> LLMParsedResponse | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    has_report_marker = any(marker in normalized_text for marker in PAYMENT_CALENDAR_REPORT_MARKERS)
    if not has_report_marker and not payment_calendar_context:
        return None

    if not has_payment_calendar_metric_marker(normalized_text):
        return None

    metrics = resolve_payment_calendar_metric(normalized_text)
    article = extract_payment_calendar_article_filter(normalized_text)
    if article is None:
        return None

    state_delta: dict[str, object] = {
        "report_type": "payment_calendar",
        "metrics": metrics,
        "filters": {"article": article},
        "group_by": [],
    }
    project = resolve_payment_calendar_project(normalized_text)
    if project:
        state_delta["project"] = project
    period_label = resolve_payment_calendar_period_label(normalized_text)
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_unsupported_group_by_request_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None
    if not any(marker in normalized_text for marker in PAYMENT_CALENDAR_REPORT_MARKERS):
        return None

    group_by = resolve_payment_calendar_unsupported_group_by(normalized_text)
    if group_by is None:
        return None

    state_delta: dict[str, object] = {
        "report_type": "payment_calendar",
        "metrics": resolve_payment_calendar_metric(normalized_text),
        "group_by": [group_by],
        "filters": {},
    }
    project = resolve_payment_calendar_project(normalized_text)
    if project:
        state_delta["project"] = project
    period_label = resolve_payment_calendar_period_label(normalized_text)
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_unsupported_metric_request_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None
    if not any(marker in normalized_text for marker in PAYMENT_CALENDAR_REPORT_MARKERS):
        return None

    unsupported_metric = find_payment_calendar_unsupported_metric(normalized_text)
    if unsupported_metric is None:
        return None

    state_delta: dict[str, object] = {
        "report_type": "payment_calendar",
        "metrics": resolve_payment_calendar_metric(normalized_text),
        "filters": {"article": unsupported_metric},
        "group_by": [],
    }
    project = resolve_payment_calendar_project(normalized_text)
    if project:
        state_delta["project"] = project
    period_label = resolve_payment_calendar_period_label(normalized_text)
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


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

    if any(marker in normalized_text for marker in ("по стать", "статьи", "подроб", "детал")):
        return {"metrics": resolve_payment_calendar_metric(normalized_text), "view": "details", "filters": {}}

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
        "balance_start": ("остаток на начал", "начал"),
        "balance_end": ("остаток на конец", "конец"),
        "income": ("поступ",),
        "payments": ("итого платеж", "платежи", "расход"),
        "details": ("стать", "детал", "подроб"),
    }
    for view, aliases in view_markers.items():
        if any(alias in normalized_text for alias in aliases):
            return {"metrics": ["plan", "fact", "deviation"], "view": view, "filters": {}}
    return None


def build_payment_calendar_view_correction(
    text: str | None,
    *,
    payment_calendar_context: bool = False,
) -> LLMParsedResponse | None:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return None

    has_report_marker = any(marker in normalized_text for marker in PAYMENT_CALENDAR_REPORT_MARKERS)
    if not has_report_marker and not payment_calendar_context:
        return None

    list_markers = {"какие", "какой", "список", "перечень", "есть", "доступные"}
    is_list_question = any(marker in normalized_text for marker in list_markers)
    if "раздел" in normalized_text and is_list_question:
        return LLMParsedResponse(
            intent=Intent.DIMENSION_QUERY,
            state_delta=StateDelta.model_validate(
                {
                    "report_type": "payment_calendar",
                    "dimension": "article_kind",
                    "filters": {},
                },
            ),
            confidence=1,
        )
    if "стат" in normalized_text and is_list_question:
        filters = {"article_kind": "detail"} if "расход" in normalized_text else {}
        return LLMParsedResponse(
            intent=Intent.DIMENSION_QUERY,
            state_delta=StateDelta.model_validate(
                {
                    "report_type": "payment_calendar",
                    "dimension": "article",
                    "filters": filters,
                },
            ),
            confidence=1,
        )

    correction = resolve_payment_calendar_metric_or_view_correction(normalized_text)
    if correction is None:
        if "остат" in normalized_text and (has_report_marker or payment_calendar_context):
            state_delta: dict[str, object] = {
                "report_type": "payment_calendar",
                "metrics": ["plan", "fact", "deviation"],
                "filters": {"article_kind": ["balance_start", "balance_end"]},
                "group_by": ["article_kind"],
            }
            project = resolve_payment_calendar_project(normalized_text)
            if project:
                state_delta["project"] = project
            period_label = resolve_payment_calendar_period_label(normalized_text)
            if period_label:
                state_delta["period"] = {"label": period_label}
            return LLMParsedResponse(
                intent=Intent.DATA_QUERY,
                state_delta=StateDelta.model_validate(state_delta),
                confidence=1,
            )
        return None
    if correction["view"] is None:
        return None

    state_delta: dict[str, object] = {
        "report_type": "payment_calendar",
        "metrics": correction["metrics"],
        "view": correction["view"],
        "filters": correction["filters"] or {},
        "group_by": [],
    }
    project = resolve_payment_calendar_project(normalized_text)
    if project:
        state_delta["project"] = project
    period_label = resolve_payment_calendar_period_label(normalized_text)
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


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


def is_payment_calendar_article_reset_request(text: str | None) -> bool:
    normalized_text = normalize_search_text(text or "")
    if not normalized_text:
        return False
    return any(
        marker in normalized_text
        for marker in (
            "без статьи",
            "без фильтра",
            "в целом",
            "общий",
            "итоги",
            "по всем статьям",
        )
    )


def build_failed_article_correction(
    state: dict[str, object] | None,
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse] | None:
    if not state or state.get(CONTEXT_BLOCKED_AFTER_ERROR) is not True:
        return None
    if state.get(FAILED_QUERY_ERROR) != "article_not_found":
        return None

    failed_state = state.get(FAILED_QUERY_STATE)
    if not isinstance(failed_state, dict):
        return None

    period_label = resolve_payment_calendar_period_label(text)
    project = resolve_payment_calendar_project(text)
    reset_article = is_payment_calendar_article_reset_request(text)
    if period_label is None and project is None and not reset_article:
        return None

    corrected_state = dict(failed_state)
    delta_data: dict[str, object] = {}
    if period_label is not None:
        period = {"label": period_label}
        corrected_state["period"] = period
        delta_data["period"] = period
    if project is not None:
        corrected_state["project"] = project
        delta_data["project"] = project
    if reset_article:
        filters = dict(corrected_state.get("filters") or {})
        filters.pop("article", None)
        corrected_state["filters"] = filters
        delta_data["filters"] = filters

    corrected_state["awaiting_clarification"] = False
    corrected_state["clarification_target"] = None
    corrected_state["clarification_base_state"] = None
    corrected_state["clarification_kind"] = None
    corrected_state["clarification_options"] = []
    corrected_state.pop("pending_action", None)
    corrected_state.pop("pending_payload", None)
    corrected_state = clear_failed_query_markers(corrected_state)

    if corrected_state.get("metrics"):
        delta_data["metrics"] = corrected_state["metrics"]
    parsed_response = LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(delta_data),
        confidence=1,
    )
    return corrected_state, parsed_response
