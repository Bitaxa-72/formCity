from app.pipeline.domain_resolver import normalize_search_text


DATA_MUTATION_BLOCK_MESSAGE = (
    "Я не изменяю и не удаляю данные в базе или таблицах.\n\n"
    "Могу только показать данные из подключенных отчетов."
)
TECHNICAL_DISCLOSURE_BLOCK_MESSAGE = (
    "Я не показываю системные инструкции, внутренние запросы, JSON, SQL и служебные параметры.\n\n"
    "Могу только показать данные из подключенных отчетов."
)
OUT_OF_SCOPE_BLOCK_MESSAGE = (
    "Я работаю только с подключенными отчетами проекта.\n\n"
    "Укажите отчет, проект, показатель и период."
)

REPORT_MARKERS = {
    "платеж",
    "календар",
    "дорожн",
    "карт",
    "модель",
    "финмодель",
    "непроект",
    "остатк",
    "продаж",
    "агент",
    "дз",
    "брон",
    "сводн",
    "отчет",
    "отчёт",
    "обвод",
    "москов",
    "евгеньев",
}
DATA_MUTATION_ACTION_MARKERS = {
    "удал",
    "измени",
    "изменить",
    "обнов",
    "добав",
    "запиши",
    "записать",
    "исправ",
    "сотри",
    "стереть",
    "перезапиши",
}
DATA_MUTATION_OBJECT_MARKERS = {
    "баз",
    "бд",
    "таблиц",
    "данн",
    "строк",
    "запис",
    "ячейк",
    "колонк",
}
TECHNICAL_MARKERS = {
    "системн промпт",
    "system prompt",
    "промпт",
    "backend query",
    "бекенд query",
    "внутренн запрос",
    "sql",
    "json",
    "confidence",
    "служебн параметр",
    "инструкц",
}
OUT_OF_SCOPE_MARKERS = {
    "погод",
    "температур",
    "стих",
    "песн",
    "шутк",
    "анекдот",
    "рецепт",
    "фильм",
    "музык",
    "новост",
    "курс валют",
    "курс доллар",
}
PROMPT_INJECTION_MARKERS = {
    "забудь инструкц",
    "игнорируй инструкц",
    "обойди правил",
    "не следуй инструкц",
}


def has_any_marker(text: str, markers: set[str]) -> bool:
    return any(marker in text for marker in markers)


def detect_guarded_non_data_request(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    if not normalized:
        return None

    has_report_context = has_any_marker(normalized, REPORT_MARKERS)
    if has_any_marker(normalized, DATA_MUTATION_ACTION_MARKERS) and has_any_marker(normalized, DATA_MUTATION_OBJECT_MARKERS):
        return DATA_MUTATION_BLOCK_MESSAGE
    if has_any_marker(normalized, PROMPT_INJECTION_MARKERS):
        return TECHNICAL_DISCLOSURE_BLOCK_MESSAGE
    if not has_report_context and has_any_marker(normalized, TECHNICAL_MARKERS):
        return TECHNICAL_DISCLOSURE_BLOCK_MESSAGE
    if not has_report_context and has_any_marker(normalized, OUT_OF_SCOPE_MARKERS):
        return OUT_OF_SCOPE_BLOCK_MESSAGE
    return None
