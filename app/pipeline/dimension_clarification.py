from dataclasses import dataclass, field

from app.pipeline.domain_resolver import normalize_search_text


@dataclass(frozen=True)
class DimensionClarification:
    matched: bool
    dimension: str | None = None
    filters: dict[str, object] = field(default_factory=dict)


PROJECT_MARKERS = ("проект", "объект")
PERIOD_MARKERS = ("период", "месяц", "месяцы", "дата", "даты")
ARTICLE_MARKERS = ("стат",)
EXPENSE_MARKERS = ("расход", "затрат")
ROW_KIND_MARKERS = ("тип строк", "типы строк", "вид строк", "виды строк", "категор", "строк", "раздел")


def has_any_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def resolve_dimension_clarification(text: str | None) -> DimensionClarification:
    normalized = normalize_search_text(text or "")
    if not normalized:
        return DimensionClarification(matched=False)

    if has_any_marker(normalized, PROJECT_MARKERS):
        return DimensionClarification(matched=True, dimension="project")

    if has_any_marker(normalized, PERIOD_MARKERS):
        return DimensionClarification(matched=True, dimension="period_month")

    if has_any_marker(normalized, ROW_KIND_MARKERS):
        return DimensionClarification(matched=True, dimension="article_kind")

    if has_any_marker(normalized, ARTICLE_MARKERS):
        filters: dict[str, object] = {}
        if has_any_marker(normalized, EXPENSE_MARKERS):
            filters["article_kind"] = "detail"
        return DimensionClarification(matched=True, dimension="article", filters=filters)

    if has_any_marker(normalized, EXPENSE_MARKERS):
        return DimensionClarification(matched=True, dimension="article", filters={"article_kind": "detail"})

    return DimensionClarification(matched=False)
