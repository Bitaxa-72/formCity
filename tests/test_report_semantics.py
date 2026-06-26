from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics


def test_payment_calendar_summary_view_becomes_total_rows_query() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "all",
                "period": {"from": "2026-03-01", "to": "2026-03-31", "label": "март"},
                "view": "summary",
            },
        ),
    )

    assert frame.ready is True
    assert frame.metrics == ["plan", "fact", "deviation"]
    assert frame.filters == {"article_kind": ["balance_start", "income_total", "payment_total", "balance_end"]}
    assert frame.group_by == ["project", "article_kind"]


def test_payment_calendar_details_view_becomes_article_breakdown() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
                "view": "details",
            },
        ),
    )

    assert frame.metrics == ["plan", "fact", "deviation"]
    assert frame.filters == {"article_kind": ["detail"]}
    assert frame.group_by == ["article"]


def test_payment_calendar_article_filter_wins_over_view() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "metrics": ["fact"],
                "view": "summary",
                "filters": {"article": "Реклама"},
            },
        ),
    )

    assert frame.metrics == ["fact"]
    assert frame.filters == {"article": "Реклама"}
    assert frame.group_by == []


def test_payment_calendar_balance_start_view_becomes_balance_start_filter() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
                "view": "balance_start",
            },
        ),
    )

    assert frame.metrics == ["plan", "fact", "deviation"]
    assert frame.filters == {"article_kind": ["balance_start"]}
    assert frame.group_by == []


def test_payment_calendar_balance_end_view_becomes_balance_end_filter() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31", "label": "май"},
                "view": "balance_end",
            },
        ),
    )

    assert frame.metrics == ["plan", "fact", "deviation"]
    assert frame.filters == {"article_kind": ["balance_end"]}
    assert frame.group_by == []
