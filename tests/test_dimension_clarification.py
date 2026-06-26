from app.pipeline.dimension_clarification import resolve_dimension_clarification


def test_resolve_dimension_clarification_article() -> None:
    resolution = resolve_dimension_clarification("статьи")

    assert resolution.matched is True
    assert resolution.dimension == "article"
    assert resolution.filters == {}


def test_resolve_dimension_clarification_expense_articles() -> None:
    resolution = resolve_dimension_clarification("список статей расходов")

    assert resolution.matched is True
    assert resolution.dimension == "article"
    assert resolution.filters == {"article_kind": "detail"}


def test_resolve_dimension_clarification_expenses_without_article_word() -> None:
    resolution = resolve_dimension_clarification("расходы")

    assert resolution.matched is True
    assert resolution.dimension == "article"
    assert resolution.filters == {"article_kind": "detail"}


def test_resolve_dimension_clarification_projects() -> None:
    resolution = resolve_dimension_clarification("какие проекты")

    assert resolution.matched is True
    assert resolution.dimension == "project"


def test_resolve_dimension_clarification_periods() -> None:
    resolution = resolve_dimension_clarification("месяцы")

    assert resolution.matched is True
    assert resolution.dimension == "period_month"


def test_resolve_dimension_clarification_row_kinds() -> None:
    resolution = resolve_dimension_clarification("типы строк")

    assert resolution.matched is True
    assert resolution.dimension == "article_kind"


def test_resolve_dimension_clarification_ignores_unrelated_text() -> None:
    resolution = resolve_dimension_clarification("план")

    assert resolution.matched is False
    assert resolution.dimension is None
