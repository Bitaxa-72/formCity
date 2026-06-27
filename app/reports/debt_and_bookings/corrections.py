import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


DEBT_MARKERS = ("дз", "дебитор", "долг", "брон")
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


def normalize_debt_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_debt_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in DEBT_MARKERS)


def extract_debt_period_label(text: str | None) -> str | None:
    normalized_text = normalize_debt_text(text)
    pattern = r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    return " ".join(part for part in match.groups() if part)


def debt_response(
    view: str,
    metrics: list[str],
    filters: dict[str, object] | None = None,
    dimension: str | None = None,
    group_by: list[str] | None = None,
    intent: Intent = Intent.DATA_QUERY,
    text: str | None = None,
) -> LLMParsedResponse:
    state_delta: dict[str, object] = {
        "report_type": "debt_and_bookings",
        "view": view,
        "metrics": metrics,
        "filters": filters or {},
        "group_by": group_by or [],
    }
    if dimension:
        state_delta["dimension"] = dimension
    period_label = extract_debt_period_label(text)
    if period_label:
        state_delta["period"] = {"label": period_label}
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_debt_and_bookings_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_debt_text(text)
    if not normalized_text or not has_debt_marker(normalized_text):
        return None

    if any(marker in normalized_text for marker in ("какие периоды", "доступные периоды", "какие месяцы", "какие срезы")):
        return debt_response("debt_bookings_available_periods", [], dimension="snapshot_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("статусы отказ", "какие статусы")):
        return debt_response("debt_bookings_available_statuses", [], dimension="status", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("способы оплат", "типы оплат")):
        return debt_response("debt_bookings_available_payment_types", [], dimension="payment_type", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие типы", "типы строк", "какие разделы")):
        return debt_response("debt_bookings_available_kinds", [], dimension="item_kind", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("по номерам помещ", "по помещен", "в разрезе помещ")):
        return debt_response(
            "debt_bookings_summary",
            ["debt_item_count", "debt_total_amount"],
            group_by=["unit_number"],
            text=text,
        )
    if any(marker in normalized_text for marker in ("номера помещ", "какие помещ", "список помещ")):
        return debt_response("debt_bookings_available_unit_numbers", [], dimension="unit_number", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("отказы", "отказники", "отказались")):
        return debt_response(
            "debt_bookings_refusals",
            ["debt_refusal_count", "debt_refusal_area", "debt_refusal_full_price"],
            text=text,
        )
    if any(marker in normalized_text for marker in ("отклон", "план факт", "факт оплат", "остаток по оплат")):
        return debt_response(
            "debt_bookings_deviations",
            ["debt_plan_amount", "debt_updated_plan_amount", "debt_fact_payment_amount", "debt_remaining_amount"],
            text=text,
        )
    if any(marker in normalized_text for marker in ("помесяч", "по месяц", "график")):
        return debt_response("debt_bookings_monthly", ["debt_monthly_value"], text=text)
    if "просроч" in normalized_text:
        return debt_response("debt_bookings_overdue", ["debt_item_count", "debt_total_amount"], text=text)
    if "текущ" in normalized_text:
        return debt_response("debt_bookings_current", ["debt_item_count", "debt_total_amount"], text=text)
    if "зарегистр" in normalized_text:
        return debt_response("debt_bookings_registered", ["debt_item_count", "debt_total_amount"], text=text)
    if "брон" in normalized_text and "дз" not in normalized_text and "дебитор" not in normalized_text:
        return debt_response("debt_bookings_bookings", ["debt_item_count", "debt_total_amount"], text=text)

    return debt_response("debt_bookings_summary", ["debt_item_count", "debt_total_amount"], text=text)
