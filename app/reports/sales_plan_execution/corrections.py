import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


SALES_PLAN_MARKERS = (
    "исполнение плана продаж",
    "выполнение плана продаж",
    "план продаж",
)
SEGMENT_ALIASES = {
    "апартамент": "sales_plan_apartments",
    "апарты": "sales_plan_apartments",
    "ресторан": "sales_plan_restaurant",
}
MONTHS = (
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


def normalize_sales_plan_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_sales_plan_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in SALES_PLAN_MARKERS)


def extract_period_label(text: str | None) -> str | None:
    normalized_text = normalize_sales_plan_text(text)
    pattern = r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    return " ".join(part for part in match.groups() if part)


def sales_plan_response(
    view: str,
    metrics: list[str],
    filters: dict[str, object] | None = None,
    dimension: str | None = None,
    intent: Intent = Intent.DATA_QUERY,
    text: str | None = None,
) -> LLMParsedResponse:
    state_delta: dict[str, object] = {
        "report_type": "sales_plan_execution",
        "project": "obvodny",
        "view": view,
        "metrics": metrics,
        "filters": filters or {},
        "group_by": [],
    }
    if dimension:
        state_delta["dimension"] = dimension
    period_label = extract_period_label(text)
    if period_label:
        state_delta["period"] = {"label": period_label}
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_sales_plan_execution_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_sales_plan_text(text)
    if not normalized_text or not has_sales_plan_marker(normalized_text):
        return None

    if any(marker in normalized_text for marker in ("какие срезы", "доступные срезы", "версии отчета")):
        return sales_plan_response("sales_plan_available_snapshots", [], dimension="snapshot_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие сегменты", "сегменты", "типы помещений")):
        return sales_plan_response("sales_plan_available_segments", [], dimension="segment", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие показатели", "метрики", "что есть")):
        return sales_plan_response("sales_plan_available_metrics", [], dimension="metric_key", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие сценарии", "план факт прогноз", "сценарии")):
        return sales_plan_response("sales_plan_available_scenarios", [], dimension="scenario", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие блоки", "разделы отчета", "типы периодов")):
        return sales_plan_response("sales_plan_available_blocks", [], dimension="block_kind", intent=Intent.DIMENSION_QUERY, text=text)

    filters: dict[str, object] = {}
    if "факт прогноз" in normalized_text or "факт плюс прогноз" in normalized_text:
        filters["scenario"] = "fact_forecast"
    elif "актуализ" in normalized_text:
        filters["scenario"] = "fact_actualized_forecast"
    elif "остат" in normalized_text and "к продаже" in normalized_text:
        filters["scenario"] = "remaining_to_sell"
    elif "отклон" in normalized_text:
        filters["scenario"] = "deviation"
    elif "прогноз" in normalized_text:
        filters["scenario"] = "forecast"
    elif "факт" in normalized_text:
        filters["scenario"] = "fact"
    elif "план" in normalized_text:
        filters["scenario"] = "plan"

    if any(marker in normalized_text for marker in ("по сегмент", "по тип", "разбивка", "в разрезе")):
        return sales_plan_response("sales_plan_by_segments", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("месяч", "за месяц", "конкретный месяц")):
        return sales_plan_response("sales_plan_month", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("итого год", "за год", "2026")):
        return sales_plan_response("sales_plan_year", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("весь проект", "итого проект", "общий итог")):
        return sales_plan_response("sales_plan_lifetime", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("цена", "за метр", "м2")):
        return sales_plan_response("sales_plan_price_per_sqm", [], filters=filters, text=text)

    for marker, view in SEGMENT_ALIASES.items():
        if marker in normalized_text:
            return sales_plan_response(view, [], filters=filters, text=text)

    metrics = []
    if any(marker in normalized_text for marker in ("поступ", "денежн", "дс")):
        metrics.append("sales_plan_cash_receipts")
    if any(marker in normalized_text for marker in ("площад", "квадрат", "м2")):
        metrics.append("sales_plan_contract_area_sqm")
    if any(marker in normalized_text for marker in ("сделк", "штук", "количество")):
        metrics.append("sales_plan_contract_count")
    if any(marker in normalized_text for marker in ("продаж", "выруч")):
        metrics.append("sales_plan_revenue")

    return sales_plan_response("sales_plan_summary", metrics, filters=filters, text=text)
