from app.pipeline.domain_resolver import format_period_phrase, format_project_phrase, normalize_search_text
from app.pipeline.query_frame import QueryPeriod


PENDING_SHOW_AVAILABLE_ARTICLES = "show_available_articles"
PENDING_CONFIRMATIONS = {
    "да",
    "давай",
    "lf",
    "lfdfq",
    "покажи",
    "показать",
    "список",
    "покажи список",
    "покажи статьи",
    "доступные статьи",
    "какие есть",
    "что есть",
    "можно",
    "ок",
    "окей",
    "ага",
    "да покажи",
    "давай список",
}
PENDING_CANCELLATIONS = {
    "нет",
    "не надо",
    "не нужно",
    "отмена",
    "отмени",
    "забей",
    "не показывай",
}
PENDING_CANCEL_MESSAGE = "Ок, не показываю список."
PENDING_UNCLEAR_MESSAGE = 'Не понял ответ. Напишите "да", чтобы показать доступные статьи, или задайте новый запрос полностью.'


def clear_pending_action(state: dict[str, object] | None) -> dict[str, object]:
    updated = dict(state or {})
    updated.pop("pending_action", None)
    updated.pop("pending_payload", None)
    return updated


def classify_pending_response(text: str | None) -> str:
    normalized = normalize_search_text(text or "")
    if normalized in PENDING_CANCELLATIONS:
        return "cancel"
    if len(normalized.split()) <= 4 and normalized in PENDING_CONFIRMATIONS:
        return "confirm"
    if normalized and len(normalized) <= 2 and normalized != "it":
        return "unclear"
    return "new_query"


def build_available_articles_message(articles: list[str], payload: dict[str, object]) -> str:
    period = QueryPeriod.model_validate(payload.get("period") or {})
    title = (
        "Доступные статьи в платежном календаре "
        f"по {format_project_phrase(payload.get('project') if isinstance(payload.get('project'), str) else None)} "
        f"за {format_period_phrase(period)}:"
    )
    if not articles:
        return title + "\n\nНе нашел статей за этот период."
    return title + "\n\n" + "\n".join(f"- {article}" for article in articles)
