import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


STOCK_MARKERS = ("остат", "экспозиц", "склад", "в продаже")
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


def normalize_stock_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_stock_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in STOCK_MARKERS)


def extract_stock_period_label(text: str | None) -> str | None:
    normalized_text = normalize_stock_text(text)
    pattern = r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    return " ".join(part for part in match.groups() if part)


def stock_response(view: str, metrics: list[str], filters: dict[str, object] | None = None, dimension: str | None = None, intent: Intent = Intent.DATA_QUERY, text: str | None = None) -> LLMParsedResponse:
    state_delta: dict[str, object] = {
        "report_type": "stock_for_sale",
        "view": view,
        "metrics": metrics,
        "filters": filters or {},
        "group_by": [],
    }
    if dimension:
        state_delta["dimension"] = dimension
    period_label = extract_stock_period_label(text)
    if period_label:
        state_delta["period"] = {"label": period_label}
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_stock_for_sale_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_stock_text(text)
    if not normalized_text or not has_stock_marker(normalized_text):
        return None

    if any(marker in normalized_text for marker in ("какие периоды", "доступные периоды", "какие месяцы", "какие срезы")):
        return stock_response("stock_available_periods", [], dimension="snapshot_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие типы", "типы объектов", "категории", "что есть")):
        return stock_response("stock_available_property_types", [], dimension="property_type", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие этажи", "список этаж", "этажи есть")):
        return stock_response("stock_available_floors", [], dimension="floor_number", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("по этаж", "этажам", "разбивка по этаж")):
        return stock_response("stock_by_floors", [], text=text)
    if "в работе" in normalized_text:
        return stock_response("stock_in_work", [], text=text)
    if any(marker in normalized_text for marker in ("апартамент", "апарты")):
        return stock_response("stock_apartments", [], text=text)
    if any(marker in normalized_text for marker in ("кладов", "кладовые")):
        return stock_response("stock_storage", [], text=text)
    if any(marker in normalized_text for marker in ("ресторан", "общепит")):
        return stock_response("stock_restaurants", [], text=text)
    if any(marker in normalized_text for marker in ("1 этаж", "первый этаж")):
        return stock_response("stock_first_floor", [], text=text)
    if any(marker in normalized_text for marker in ("цена метра", "цена за метр", "за м2", "за метр")):
        return stock_response("stock_price_per_sqm", [], text=text)
    if any(marker in normalized_text for marker in ("суммы", "дду", "дупт", "наценка")):
        return stock_response("stock_amounts", [], text=text)
    if any(marker in normalized_text for marker in ("детально", "подробно", "по строкам")):
        return stock_response("stock_details", [], text=text)

    return stock_response("stock_summary", [], text=text)
