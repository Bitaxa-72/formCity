from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_compatibility import check_report_compatibility
from app.pipeline.report_semantics import apply_report_semantics


def test_check_report_compatibility_rejects_sales_metric_for_payment_calendar() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["fact"],
        },
    )

    result = check_report_compatibility(frame, "платежный календарь московский выручка за май")

    assert result.valid is False
    assert result.error == "metric_not_supported_for_payment_calendar"
    assert result.message is not None
    assert 'нет показателя "выручка"' in result.message


def test_check_report_compatibility_allows_payment_calendar_article() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["fact"],
            "filters": {"article": "реклама"},
        },
    )

    result = check_report_compatibility(frame, "платежный календарь московский факт по рекламе за май")

    assert result.valid is True
    assert result.error is None
    assert result.message is None


def test_check_report_compatibility_rejects_foreign_group_by_for_payment_calendar() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["plan"],
            "group_by": ["floor"],
        },
    )

    result = check_report_compatibility(frame, "платежный календарь московский план по этажам за май")

    assert result.valid is False
    assert result.error == "group_by_not_supported_for_payment_calendar"
    assert result.message is not None
    assert "нет разбивки по этажам" in result.message
    assert "по статьям" in result.message


def test_check_report_compatibility_rejects_room_type_group_by_for_payment_calendar() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["fact"],
            "group_by": ["room_type"],
        },
    )

    result = check_report_compatibility(frame, "платежный календарь московский факт по типам помещений за май")

    assert result.valid is False
    assert result.error == "group_by_not_supported_for_payment_calendar"
    assert result.message is not None
    assert "нет разбивки по типам помещений" in result.message


def test_check_report_compatibility_allows_payment_calendar_article_group_by() -> None:
    frame = build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "moskovsky",
            "period": {"label": "май"},
            "metrics": ["plan"],
            "group_by": ["article"],
        },
    )

    result = check_report_compatibility(frame, "платежный календарь план по статьям за май")

    assert result.valid is True


def test_check_report_compatibility_rejects_floor_for_roadmap() -> None:
    frame = apply_report_semantics(build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "roadmap",
            "project": "all",
            "period": {"label": "апрель"},
            "metrics": ["duration_min", "duration_max"],
            "view": "full_roadmap",
        },
    ))

    result = check_report_compatibility(frame, "сколько этажей?")

    assert result.valid is False
    assert result.error == "metric_not_supported_for_roadmap"
    assert result.message is not None
    assert 'нет показателя "этажи"' in result.message
