import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


AGENT_MARKERS = ("агент", "агентск", "вознагражден")
AGENT_METRIC_MARKERS = ("остат", "оплач", "сделк", "площад")
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
AGENT_FILTER_STOP_WORDS = {
    "отчет",
    "по",
    "агентам",
    "агент",
    "агенты",
    "агентское",
    "агентский",
    "агентская",
    "вознаграждение",
    "вознаграждения",
    "вознагражден",
    "остаток",
    "остатки",
    "остатка",
    "оплачено",
    "оплачен",
    "сделки",
    "сделок",
    "площадь",
    "сумма",
    "сколько",
    "покажи",
    "дай",
    "за",
    "срез",
    "последний",
    "актуальный",
    "апрель",
    "апреля",
    "март",
    "марта",
    "февраль",
    "февраля",
    "в",
    "продаже",
}


def normalize_agents_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_agent_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in AGENT_MARKERS)


def has_agent_metric_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in AGENT_METRIC_MARKERS)


def extract_agents_period_label(text: str | None) -> str | None:
    normalized_text = normalize_agents_text(text)
    pattern = r"\b(" + "|".join(MONTHS) + r")\b(?:\s+(\d{4}))?"
    match = re.search(pattern, normalized_text)
    if not match:
        return None
    return " ".join(part for part in match.groups() if part)


def format_agent_token(token: str) -> str:
    if len(token) <= 4:
        return token.upper()
    return token[:1].upper() + token[1:]


def extract_agent_contains(text: str | None) -> str | None:
    tokens = [token for token in normalize_agents_text(text).split() if token not in AGENT_FILTER_STOP_WORDS and not token.isdigit()]
    if not tokens:
        return None

    legal_forms = {"ооо", "ип", "ао", "пао"}
    tokens = [token for token in tokens if token not in legal_forms]
    if not tokens:
        return None
    return " ".join(format_agent_token(token) for token in tokens)


def agents_response(
    view: str,
    metrics: list[str],
    filters: dict[str, object] | None = None,
    dimension: str | None = None,
    group_by: list[str] | None = None,
    intent: Intent = Intent.DATA_QUERY,
    text: str | None = None,
) -> LLMParsedResponse:
    state_delta: dict[str, object] = {
        "report_type": "agents_report",
        "view": view,
        "metrics": metrics,
        "filters": filters or {},
        "group_by": group_by or [],
    }
    if dimension:
        state_delta["dimension"] = dimension
    period_label = extract_agents_period_label(text)
    if period_label:
        state_delta["period"] = {"label": period_label}
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def build_agents_report_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_agents_text(text)
    agent_contains = extract_agent_contains(text)
    if not normalized_text or not (has_agent_marker(normalized_text) or (has_agent_metric_marker(normalized_text) and agent_contains)):
        return None

    if any(marker in normalized_text for marker in ("какие срезы", "доступные срезы", "версии отчета")):
        return agents_response("agents_available_snapshots", [], dimension="snapshot_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("бюджетные месяцы", "месяцы бюджета")):
        return agents_response("agents_available_budget_months", [], dimension="budget_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("месяцы оплат", "месяцы графика", "периоды оплат")):
        return agents_response("agents_available_payment_months", [], dimension="payment_period_month", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие графики", "типы графиков", "дду уступка")):
        return agents_response("agents_available_value_kinds", [], dimension="value_kind", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("какие агенты", "список агентов", "наименования агентов")):
        return agents_response("agents_available_agents", [], dimension="agent", intent=Intent.DIMENSION_QUERY, text=text)
    if any(marker in normalized_text for marker in ("номера помещ", "какие помещ", "список помещ")):
        return agents_response("agents_available_unit_numbers", [], dimension="unit_number", intent=Intent.DIMENSION_QUERY, text=text)

    if any(marker in normalized_text for marker in ("помесяч", "по месяц", "график")):
        return agents_response("agents_monthly", ["agents_monthly_value"], text=text)
    if any(marker in normalized_text for marker in ("по агент", "по наименован")):
        return agents_response("agents_summary", [], group_by=["agent"], text=text)
    if any(marker in normalized_text for marker in ("по помещ", "по номерам помещ")):
        return agents_response("agents_summary", [], group_by=["unit_number"], text=text)
    if any(marker in normalized_text for marker in ("по бюдж", "бюджет")):
        return agents_response("agents_by_budget_month", [], text=text)
    if any(marker in normalized_text for marker in ("дду", "уступк", "меблиров")):
        return agents_response("agents_ddu", [], text=text)

    metrics = []
    if any(marker in normalized_text for marker in ("сколько", "количество", "число сдел")):
        metrics.append("agents_deal_count")
    if "площад" in normalized_text:
        metrics.append("agents_area_sqm")
    if any(marker in normalized_text for marker in ("вознагражден", "агентск")):
        metrics.append("agents_commission_amount")
    if "оплач" in normalized_text:
        metrics.append("agents_paid_amount")
    if "остат" in normalized_text:
        metrics.append("agents_remaining_amount")

    filters = {}
    if agent_contains:
        filters["agent_contains"] = agent_contains

    return agents_response("agents_summary", metrics, filters=filters, text=text)
