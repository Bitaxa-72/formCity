import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta
from app.pipeline.failed_query import (
    CONTEXT_BLOCKED_AFTER_ERROR,
    FAILED_QUERY_ERROR,
    FAILED_QUERY_STATE,
    clear_failed_query_markers,
)
from app.reports.model.catalog import MODEL_FINANCIAL_SUMMARY_METRICS


MODEL_SUMMARY_MARKERS = (
    "модел",
    "финансовая модел",
)
MODEL_SUMMARY_VIEW_MARKERS = (
    "свод",
    "итог",
    "kpi",
    "показател",
    "кратк",
)
MODEL_SNAPSHOT_MARKERS = (
    "срез",
    "верс",
    "месяц",
    "период",
)
MODEL_MONTHS = (
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
MODEL_EXPLICIT_METRIC_MARKERS = (
    "выруч",
    "себестоим",
    "валов",
    "чист",
    "npv",
    "нпв",
    "roe",
    "рое",
    "llcr",
    "ллср",
    "лср",
    "пир",
    "площад",
    "помещен",
)
MODEL_METRIC_ALIASES = {
    "model_revenue": ("выруч",),
    "model_cost_of_sales": ("себестоим",),
    "model_gross_profit": ("валов",),
    "model_net_profit": ("чист",),
    "model_npv": ("npv", "нпв"),
    "model_roe": ("roe", "рое", "процент"),
    "model_llcr": ("llcr", "ллср", "лср"),
    "model_units_count": ("количество помещений",),
    "model_pir_total": ("пир",),
}
MODEL_COMPARISON_MARKERS = (
    "сравнен",
)
MODEL_COMPARISON_METRICS = [
    "model_revenue",
    "model_cost_of_sales",
    "model_gross_profit",
    "model_net_profit",
    "model_npv",
    "model_roe",
    "model_llcr",
]
MODEL_AVAILABLE_METRICS_MARKERS = (
    "какие показатели",
    "какие метрики",
    "доступные показатели",
    "доступные метрики",
    "список kpi",
    "список показателей",
)
MODEL_TOTAL_AREA_MARKERS = (
    "квадратн",
    "кв метр",
    "кв м",
    "площад",
    "общая площадь",
)
MODEL_SENSITIVE_MARKERS = (
    "телефон",
    "контакт",
    "паспорт",
    "документ",
    "договор",
    "дду",
    "реквизит",
    "фио",
)
MODEL_RAW_SHEET_LIST_MARKERS = (
    "какие листы",
    "какие таблицы",
    "список листов",
    "список таблиц",
    "загруженные листы",
    "raw лист",
    "raw листы",
)
MODEL_RAW_SEARCH_MARKERS = (
    "найди",
    "найти",
    "поищи",
    "поиск",
)
MODEL_RAW_SHEET_ALIASES = {
    "fm": (
        "фм",
        "фм_",
    ),
    "fm_plan": (
        "фм план",
        "фм_план",
    ),
    "newkpi": (
        "newkpi",
        "newkpi s",
        "нью kpi",
    ),
    "newkpi_plan": (
        "newkpi план",
        "newkpi s план",
    ),
    "passport": (
        "паспорт",
    ),
    "rates": (
        "процент",
        "проценты",
    ),
    "comparison": (
        "сравнен",
    ),
    "financial_model": (
        "финмодел",
        "фин модел",
        "финансовая модел",
    ),
    "remains": (
        "остатк",
    ),
    "consolidation": (
        "для консолидац",
        "консолидац",
    ),
}
MODEL_RAW_QUERY_STOP_WORDS = {
    "модель",
    "модел",
    "финмодель",
    "финмодел",
    "фин",
    "финансовая",
    "финансовой",
    "фм",
    "newkpi",
    "kpi",
    "паспорт",
    "проценты",
    "процент",
    "сравнение",
    "сравнен",
    "остатки",
    "остатках",
    "остатк",
    "для",
    "консолидации",
    "консолидац",
    "найди",
    "найти",
    "поищи",
    "поиск",
    "лист",
    "листе",
    "листах",
    "в",
    "на",
    "по",
    "за",
    "из",
    "с",
    "и",
    "покажи",
    "строку",
    "строки",
    "строка",
    "значение",
    "значения",
    *MODEL_MONTHS,
}


def is_model_summary_request(text: str | None) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_SUMMARY_VIEW_MARKERS)


def normalize_model_text(text: str) -> str:
    normalized_text = text.casefold().replace("ё", "е")
    normalized_text = re.sub(r"[^0-9a-zа-я]+", " ", normalized_text)
    return re.sub(r"\s+", " ", normalized_text).strip()


def build_model_summary_correction(text: str | None) -> LLMParsedResponse | None:
    if not is_model_summary_request(text):
        return None

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "view": "model_summary",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def is_model_sensitive_request(text: str | None) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_SENSITIVE_MARKERS)


def build_model_sensitive_correction(text: str | None) -> LLMParsedResponse | None:
    if not is_model_sensitive_request(text):
        return None

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "view": "model_summary",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def find_model_raw_sheet(text: str | None) -> str | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None
    for sheet, aliases in MODEL_RAW_SHEET_ALIASES.items():
        if any(alias in normalized_text for alias in aliases):
            return sheet
    return None


def is_model_raw_sheet_list_request(text: str | None, model_context: bool = False) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not model_context and not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_RAW_SHEET_LIST_MARKERS)


def build_model_raw_sheet_list_correction(
    text: str | None,
    model_context: bool = False,
) -> LLMParsedResponse | None:
    if not is_model_raw_sheet_list_request(text, model_context=model_context):
        return None

    return LLMParsedResponse(
        intent=Intent.DIMENSION_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "view": "model_raw_sheets",
                "dimension": "raw_sheet",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def extract_model_raw_query(text: str | None) -> str | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None
    tokens = [
        token
        for token in normalized_text.split()
        if token not in MODEL_RAW_QUERY_STOP_WORDS
        and not token.isdigit()
        and not re.fullmatch(r"\d{4}", token)
    ]
    query = " ".join(tokens).strip()
    return query or None


def build_model_raw_rows_correction(
    text: str | None,
    model_context: bool = False,
) -> LLMParsedResponse | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None
    if not model_context and not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return None

    raw_sheet = find_model_raw_sheet(normalized_text)
    if not raw_sheet:
        return None

    period_label = extract_model_period_label(normalized_text)
    raw_query = extract_model_raw_query(normalized_text)
    is_search = any(marker in normalized_text for marker in MODEL_RAW_SEARCH_MARKERS) and raw_query is not None
    if raw_sheet == "financial_model" and not is_search:
        state_delta: dict[str, object] = {
            "report_type": "model",
            "view": "model_financial_summary",
            "metrics": MODEL_FINANCIAL_SUMMARY_METRICS,
            "filters": {},
            "group_by": [],
        }
        if period_label:
            state_delta["period"] = {"label": period_label}
        return LLMParsedResponse(
            intent=Intent.DATA_QUERY,
            state_delta=StateDelta.model_validate(state_delta),
            confidence=1,
        )

    filters: dict[str, object] = {"raw_sheet": raw_sheet}
    if is_search:
        filters["raw_query"] = raw_query

    state_delta: dict[str, object] = {
        "report_type": "model",
        "view": "model_raw_search" if is_search else "model_raw_rows",
        "metrics": [],
        "filters": filters,
        "group_by": [],
    }
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def find_model_metric_keys(text: str | None) -> list[str]:
    normalized_text = normalize_model_text(text or "")
    found = []
    for metric, aliases in MODEL_METRIC_ALIASES.items():
        if any(alias in normalized_text for alias in aliases):
            found.append(metric)
    if "model_pir_total" in found and "model_pir_per_sqm" not in found:
        found.append("model_pir_per_sqm")
    if not found and "прибыл" in normalized_text:
        found.extend(["model_gross_profit", "model_net_profit"])
    return found


def build_model_metric_correction(
    text: str | None,
    model_context: bool = False,
    fallback_period: dict[str, object] | None = None,
) -> LLMParsedResponse | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None
    if not model_context and not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return None

    metrics = find_model_metric_keys(normalized_text)
    if not metrics:
        return None

    period_label = extract_model_period_label(normalized_text)
    state_delta: dict[str, object] = {
        "report_type": "model",
        "view": "model_kpi",
        "metrics": metrics,
        "filters": {},
        "group_by": [],
    }
    if period_label:
        state_delta["period"] = {"label": period_label}
    elif fallback_period:
        state_delta["period"] = fallback_period

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_model_comparison_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return None
    if not any(marker in normalized_text for marker in MODEL_COMPARISON_MARKERS):
        return None

    period_label = extract_model_period_label(normalized_text)
    state_delta: dict[str, object] = {
        "report_type": "model",
        "view": "model_kpi",
        "metrics": MODEL_COMPARISON_METRICS,
        "filters": {},
        "group_by": [],
    }
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def is_model_available_metrics_request(text: str | None, model_context: bool = False) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not model_context and not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_AVAILABLE_METRICS_MARKERS)


def build_model_available_metrics_correction(
    text: str | None,
    model_context: bool = False,
) -> LLMParsedResponse | None:
    if not is_model_available_metrics_request(text, model_context=model_context):
        return None

    return LLMParsedResponse(
        intent=Intent.DIMENSION_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "view": "model_available_metrics",
                "dimension": "metric",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def extract_model_period_label(text: str | None) -> str | None:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return None

    pattern = r"\b(" + "|".join(MODEL_MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    return " ".join(part for part in match.groups() if part)


def is_model_period_summary_request(text: str | None) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    if not extract_model_period_label(normalized_text):
        return False
    return not any(marker in normalized_text for marker in MODEL_EXPLICIT_METRIC_MARKERS)


def build_model_period_summary_correction(text: str | None) -> LLMParsedResponse | None:
    if not is_model_period_summary_request(text):
        return None

    period_label = extract_model_period_label(text)
    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "period": {"label": period_label},
                "view": "model_summary",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def is_model_total_area_request(text: str | None) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_TOTAL_AREA_MARKERS)


def build_model_total_area_correction(text: str | None) -> LLMParsedResponse | None:
    if not is_model_total_area_request(text):
        return None

    period_label = extract_model_period_label(text)
    state_delta: dict[str, object] = {
        "report_type": "model",
        "view": "model_kpi",
        "metrics": ["model_total_area"],
        "filters": {},
        "group_by": [],
    }
    if period_label:
        state_delta["period"] = {"label": period_label}

    return LLMParsedResponse(
        intent=Intent.DATA_QUERY,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def is_model_snapshot_request(text: str | None) -> bool:
    normalized_text = normalize_model_text(text or "")
    if not normalized_text:
        return False
    if not any(marker in normalized_text for marker in MODEL_SUMMARY_MARKERS):
        return False
    return any(marker in normalized_text for marker in MODEL_SNAPSHOT_MARKERS)


def build_model_snapshot_correction(text: str | None) -> LLMParsedResponse | None:
    if not is_model_snapshot_request(text):
        return None

    return LLMParsedResponse(
        intent=Intent.DIMENSION_QUERY,
        state_delta=StateDelta.model_validate(
            {
                "report_type": "model",
                "view": "model_available_snapshots",
                "dimension": "snapshot_month",
                "metrics": [],
                "filters": {},
                "group_by": [],
            },
        ),
        confidence=1,
    )


def build_failed_model_metric_correction(
    state: dict[str, object] | None,
    text: str | None,
) -> tuple[dict[str, object], LLMParsedResponse] | None:
    if not state or state.get(CONTEXT_BLOCKED_AFTER_ERROR) is not True:
        return None
    if state.get(FAILED_QUERY_ERROR) not in {"metric_not_supported_for_model", "unknown_metric_for_model"}:
        return None

    failed_state = state.get(FAILED_QUERY_STATE)
    if not isinstance(failed_state, dict) or failed_state.get("report_type") != "model":
        return None

    metrics = find_model_metric_keys(text)
    if not metrics:
        return None

    corrected_state = dict(failed_state)
    corrected_state["view"] = "model_kpi"
    corrected_state["metrics"] = metrics
    corrected_state["filters"] = {}
    corrected_state["group_by"] = []
    corrected_state["awaiting_clarification"] = False
    corrected_state["clarification_target"] = None
    corrected_state["clarification_base_state"] = None
    corrected_state["clarification_kind"] = None
    corrected_state["clarification_options"] = []
    corrected_state = clear_failed_query_markers(corrected_state)

    delta_data: dict[str, object] = {
        "report_type": "model",
        "view": "model_kpi",
        "metrics": metrics,
        "filters": {},
        "group_by": [],
    }
    period = corrected_state.get("period")
    if isinstance(period, dict):
        delta_data["period"] = period

    return (
        corrected_state,
        LLMParsedResponse(
            intent=Intent.DATA_QUERY,
            state_delta=StateDelta.model_validate(delta_data),
            confidence=1,
        ),
    )
