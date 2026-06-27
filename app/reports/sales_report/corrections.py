import re
from datetime import date

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


SALES_MARKERS = ("продаж", "контрактац")
MONTHS = {
    "январь": 1,
    "января": 1,
    "февраль": 2,
    "февраля": 2,
    "март": 3,
    "марта": 3,
    "апрель": 4,
    "апреля": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июль": 7,
    "июля": 7,
    "август": 8,
    "августа": 8,
    "сентябрь": 9,
    "сентября": 9,
    "октябрь": 10,
    "октября": 10,
    "ноябрь": 11,
    "ноября": 11,
    "декабрь": 12,
    "декабря": 12,
}


def normalize_sales_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_sales_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in SALES_MARKERS)


def extract_sales_month(text: str | None) -> date | None:
    normalized_text = normalize_sales_text(text)
    pattern = r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    month = MONTHS[match.group(1)]
    year = int(match.group(2)) if match.group(2) else 2026
    return date(year, month, 1)


def sales_response(view: str, metrics: list[str], filters: dict[str, object] | None = None, dimension: str | None = None, intent: Intent = Intent.DATA_QUERY, text: str | None = None) -> LLMParsedResponse:
    prepared_filters = dict(filters or {})
    if "срез" not in normalize_sales_text(text):
        month = extract_sales_month(text)
        if month:
            prepared_filters["period_month"] = month.isoformat()

    state_delta: dict[str, object] = {
        "report_type": "sales_report",
        "view": view,
        "metrics": metrics,
        "filters": prepared_filters,
        "group_by": [],
    }
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_sales_report_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_sales_text(text)
    if not normalized_text or not has_sales_marker(normalized_text):
        return None

    if any(marker in normalized_text for marker in ("какие срезы", "версии отчета", "доступные срезы")):
        return sales_response("sales_available_snapshots", [], dimension="snapshot_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие месяцы", "периоды продаж", "доступные периоды")):
        return sales_response("sales_available_periods", [], dimension="period_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие сегменты", "сегменты", "типы помещений", "разделы")):
        return sales_response("sales_available_segments", [], dimension="segment", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие показатели", "метрики", "что есть")):
        return sales_response("sales_available_metrics", [], dimension="metric_key", intent=Intent.DIMENSION_QUERY, text=text)

    filters: dict[str, object] = {}
    if "факт" in normalized_text:
        filters["scenario"] = "fact"
    elif "план" in normalized_text:
        filters["scenario"] = "plan"

    if any(marker in normalized_text for marker in ("по сегмент", "по тип", "разбивка", "в разрезе")):
        return sales_response("sales_by_segments", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("помесяч", "по месяц", "динамик")):
        return sales_response("sales_monthly", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("оплат", "дду")):
        return sales_response("sales_payments", [], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("цена", "за метр", "м2")):
        return sales_response("sales_price_per_sqm", [], filters=filters, text=text)

    if any(marker in normalized_text for marker in ("апартамент", "апарты")):
        return sales_response("sales_apartments", [], filters=filters, text=text)
    if "кладов" in normalized_text:
        return sales_response("sales_storage", [], filters=filters, text=text)
    if "ресторан" in normalized_text:
        return sales_response("sales_restaurant", [], filters=filters, text=text)
    if "sh" in normalized_text:
        return sales_response("sales_sh", [], filters=filters, text=text)
    if "2 этаж" in normalized_text:
        return sales_response("sales_commercial_2_floor", [], filters=filters, text=text)
    if "1 этаж" in normalized_text or "первый этаж" in normalized_text:
        return sales_response("sales_commercial_1_floor", [], filters=filters, text=text)

    if any(marker in normalized_text for marker in ("квадрат", "площад", "метры")):
        return sales_response("sales_summary", ["sales_contract_area_sqm"], filters=filters, text=text)
    if any(marker in normalized_text for marker in ("сделк", "штук", "количество")):
        return sales_response("sales_summary", ["sales_contract_count"], filters=filters, text=text)
    if "выруч" in normalized_text:
        return sales_response("sales_summary", ["sales_contract_revenue"], filters=filters, text=text)

    return sales_response("sales_summary", [], filters=filters, text=text)
