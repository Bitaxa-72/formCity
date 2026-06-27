import re

from app.llm.dictionary import Intent
from app.llm.parser import LLMParsedResponse, StateDelta


SUMMARY_MARKERS = ("сводный отчет", "сводная таблица", "сводные таблицы", "сводная")
SHEET_KIND_ALIASES = {
    "апартамент": "residential_units",
    "квартир": "residential_units",
    "коммерц": "commercial_units",
    "кладов": "storage_units",
    "расторж": "contract_termination",
    "уступ": "assignment",
    "гарант": "guaranteed_income",
    "аренд": "guaranteed_income",
    "дат": "timeline",
    "класс": "class_summary",
    "итог": "summary_totals",
    "дкп": "sale_purchase_contract",
    "окн": "window_agreements",
    "агент": "agents",
}
HEADER_ALIASES = {
    "оплачено": "оплачено",
    "оплата": "оплачено",
    "остаток": "остаток",
    "площадь": "площадь",
    "метры": "площадь",
    "цена за метр": "цена_1_кв_м",
    "цена м2": "цена_1_кв_м",
    "цена 1 кв м": "цена_1_кв_м",
    "цена брони": "цена_брони",
}
PROJECT_ALIASES = {
    "moskovsky": ("московский", "мск"),
    "obvodny": ("обводный", "обвод"),
    "evgenievsky": ("евгеньевский", "евгеньев"),
}


def normalize_summary_text(text: str | None) -> str:
    normalized = (text or "").casefold().replace("ё", "е")
    normalized = re.sub(r"[^0-9a-zа-я]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def has_summary_marker(normalized_text: str) -> bool:
    return any(marker in normalized_text for marker in SUMMARY_MARKERS)


def summary_response(
    view: str,
    metrics: list[str] | None = None,
    filters: dict[str, object] | None = None,
    dimension: str | None = None,
    intent: Intent = Intent.DATA_QUERY,
    project: str | None = None,
) -> LLMParsedResponse:
    state_delta: dict[str, object] = {
        "report_type": "summary",
        "project": project or "all",
        "view": view,
        "metrics": metrics or [],
        "filters": filters or {},
        "group_by": [],
    }
    if dimension:
        state_delta["dimension"] = dimension
    return LLMParsedResponse(
        intent=intent,
        state_delta=StateDelta.model_validate(state_delta),
        confidence=1,
    )


def extract_sheet_kind(normalized_text: str) -> str | None:
    for marker, sheet_kind in SHEET_KIND_ALIASES.items():
        if marker in normalized_text:
            return sheet_kind
    return None


def extract_header_key(normalized_text: str) -> str | None:
    for marker, header_key in HEADER_ALIASES.items():
        if marker in normalized_text:
            return header_key
    return None


def extract_project(normalized_text: str) -> str | None:
    for project, markers in PROJECT_ALIASES.items():
        if any(marker in normalized_text for marker in markers):
            return project
    return None


def build_summary_correction(text: str | None) -> LLMParsedResponse | None:
    normalized_text = normalize_summary_text(text)
    if not normalized_text or not has_summary_marker(normalized_text):
        return None

    filters: dict[str, object] = {}
    project = extract_project(normalized_text)
    sheet_kind = extract_sheet_kind(normalized_text)
    if sheet_kind:
        filters["sheet_kind"] = sheet_kind

    if any(marker in normalized_text for marker in ("какие проекты", "список проектов")):
        return summary_response("summary_available_projects", filters=filters, dimension="project", intent=Intent.DIMENSION_QUERY, project=project)
    if any(marker in normalized_text for marker in ("какие файлы", "список файлов", "источники")):
        return summary_response("summary_available_files", filters=filters, dimension="source_file", intent=Intent.DIMENSION_QUERY, project=project)
    if any(marker in normalized_text for marker in ("какие листы", "список листов")):
        return summary_response("summary_available_sheets", filters=filters, dimension="sheet_name", intent=Intent.DIMENSION_QUERY, project=project)
    if any(marker in normalized_text for marker in ("типы листов", "виды листов", "разделы")):
        return summary_response("summary_available_sheet_kinds", filters=filters, dimension="sheet_kind", intent=Intent.DIMENSION_QUERY, project=project)
    if any(marker in normalized_text for marker in ("какие колонки", "какие поля", "какие показатели", "доступные колонки")):
        return summary_response("summary_available_headers", filters=filters, dimension="header_key", intent=Intent.DIMENSION_QUERY, project=project)
    if any(marker in normalized_text for marker in ("типы строк", "виды строк")):
        return summary_response("summary_available_row_types", filters=filters, dimension="row_type", intent=Intent.DIMENSION_QUERY, project=project)

    header_key = extract_header_key(normalized_text)
    if header_key:
        filters["header_key"] = header_key
        return summary_response("summary_values", metrics=["summary_value_sum"], filters=filters, project=project)

    if any(marker in normalized_text for marker in ("суммы", "числовые", "значения")):
        return summary_response("summary_values", metrics=["summary_numeric_cell_count", "summary_value_sum"], filters=filters, project=project)

    return summary_response("summary_overview", filters=filters, project=project)
