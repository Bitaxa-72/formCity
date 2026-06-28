from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, PaymentCalendarFact
from app.pipeline.domain_resolver import DomainResolver, normalize_search_text, select_article_from_options
from app.pipeline.query_frame import build_query_frame


def create_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def add_payment_article(
    session,
    article: str,
    order: int,
    project: str = "obvodny",
    article_kind: str = "detail",
    period_month: date = date(2026, 5, 1),
) -> None:
    session.add(
        PaymentCalendarFact(
            project=project,
            period_month=period_month,
            article=article,
            article_kind=article_kind,
            article_order=order,
        ),
    )


def build_article_frame(article: str):
    return build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "metrics": ["fact"],
            "filters": {"article_kind": "detail", "article": article},
        },
    )


def build_period_frame(from_date: str, to_date: str, project: str = "obvodny"):
    return build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": project,
            "period": {"from": from_date, "to": to_date},
            "metrics": ["fact"],
        },
    )


def build_period_label_frame(label: str, from_date: str | None = None, to_date: str | None = None):
    period = {"label": label}
    if from_date:
        period["from"] = from_date
    if to_date:
        period["to"] = to_date
    return build_query_frame(
        {
            "last_intent": "data_query",
            "report_type": "payment_calendar",
            "project": "obvodny",
            "period": period,
            "metrics": ["fact"],
        },
    )


def test_normalize_search_text_ignores_case_spaces_and_yo() -> None:
    assert normalize_search_text("  РЁКЛАМА   ООО ") == "реклама ооо"


def test_domain_resolver_matches_article_with_typo() -> None:
    session = create_session()
    add_payment_article(session, "Advertising and marketing", 1)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("advertsing"))

    assert resolution.valid is True
    assert resolution.frame.filters["article"] == "Advertising and marketing"
    assert resolution.frame.group_by == []


def test_domain_resolver_matches_article_with_repeated_letter_typo() -> None:
    session = create_session()
    add_payment_article(session, "ФОТ + налоги (ФОТ)", 1)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("фооот"))

    assert resolution.valid is True
    assert resolution.frame.filters["article"] == "ФОТ + налоги (ФОТ)"
    assert resolution.frame.group_by == []


def test_domain_resolver_uses_up_to_three_article_matches() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1)
    add_payment_article(session, "Rent equipment", 2)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("rent"))

    assert resolution.valid is True
    assert resolution.frame.filters["article"] == ["Rent equipment", "Rent office"]
    assert resolution.frame.group_by == ["article"]


def test_domain_resolver_clarifies_when_more_than_three_articles_match() -> None:
    session = create_session()
    add_payment_article(session, "Tax 1", 1)
    add_payment_article(session, "Tax 2", 2)
    add_payment_article(session, "Tax 3", 3)
    add_payment_article(session, "Tax 4", 4)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("tax"))

    assert resolution.valid is False
    assert resolution.errors == ["article_ambiguous"]
    assert resolution.clarification_question is not None
    assert resolution.details["clarification_kind"] == "article"
    assert resolution.details["article_candidates"] == ["Tax 1", "Tax 2", "Tax 3"]


def test_domain_resolver_exact_article_match_wins_over_many_fuzzy_matches() -> None:
    session = create_session()
    add_payment_article(session, "Tax 1", 1)
    add_payment_article(session, "Tax 2", 2)
    add_payment_article(session, "Tax 3", 3)
    add_payment_article(session, "Tax 4", 4)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("Tax 2"))

    assert resolution.valid is True
    assert resolution.frame.filters["article"] == "Tax 2"
    assert resolution.frame.group_by == []


def test_select_article_from_options_uses_saved_clarification_options() -> None:
    selected = select_article_from_options(
        "fot + nalogi",
        [
            "FOT + taxes (FOT)",
            "Deposits percent",
            "Some contractor",
        ],
    )

    assert selected == "FOT + taxes (FOT)"


def test_domain_resolver_reports_missing_article() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1)
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_article_frame("marketing"))

    assert resolution.valid is False
    assert resolution.errors == ["article_not_found"]


def test_domain_resolver_rejects_project_without_data() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, project="obvodny")
    add_payment_article(session, "Rent office", 2, project="moskovsky")
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_frame("2026-05-01", "2026-05-31", project="evgenievsky"))

    assert resolution.valid is False
    assert resolution.errors == ["project_data_not_found"]
    assert resolution.clarification_question == (
        "По проекту Евгеньевскому нет данных в платежном календаре. "
        "Доступные проекты: Московский, Обводный."
    )


def test_domain_resolver_rejects_period_without_data() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_frame("2026-06-01", "2026-06-30"))

    assert resolution.valid is False
    assert resolution.errors == ["period_data_not_found"]
    assert resolution.clarification_question is not None


def test_domain_resolver_rejects_missing_month_label_without_falling_back_to_all_period() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_label_frame("январь 2030"))

    assert resolution.valid is False
    assert resolution.errors == ["period_data_not_found"]


def test_domain_resolver_normalizes_day_filter_to_month() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_frame("2026-05-23", "2026-05-23"))

    assert resolution.valid is True
    assert resolution.frame.period.from_date == "2026-05-01"
    assert resolution.frame.period.to == "2026-05-31"


def test_domain_resolver_normalizes_dotted_day_label_to_month() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_label_frame("23.05.2026"))

    assert resolution.valid is True
    assert resolution.frame.period.from_date == "2026-05-01"
    assert resolution.frame.period.to == "2026-05-31"


def test_domain_resolver_uses_available_year_for_month_label() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_label_frame("май", "2023-05-01", "2023-05-31"))

    assert resolution.valid is True
    assert resolution.frame.period.from_date == "2026-05-01"
    assert resolution.frame.period.to == "2026-05-31"


def test_domain_resolver_returns_up_to_three_article_matches_grouped() -> None:
    session = create_session()
    add_payment_article(session, "ФОТ + налоги (ФОТ)", 1, project="moskovsky")
    add_payment_article(session, "Казначейство России (ФНС России) - налог на прибыль", 2, project="moskovsky")
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31"},
                "metrics": ["plan"],
                "filters": {"article": "налоги"},
            },
        ),
    )

    assert resolution.valid is True
    assert resolution.frame.filters["article"] == [
        "ФОТ + налоги (ФОТ)",
        "Казначейство России (ФНС России) - налог на прибыль",
    ]
    assert resolution.frame.group_by == ["article"]


def test_domain_resolver_matches_articles_inside_requested_period_only() -> None:
    session = create_session()
    add_payment_article(session, "Оплата в ООО", 1, project="moskovsky", period_month=date(2026, 4, 1))
    add_payment_article(session, "ИТОГО платежи", 2, project="moskovsky", article_kind="payment_total", period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "payment_calendar",
                "project": "moskovsky",
                "period": {"from": "2026-05-01", "to": "2026-05-31"},
                "metrics": ["plan"],
                "filters": {"article": "оплата"},
            },
        ),
    )

    assert resolution.valid is False
    assert resolution.errors == ["article_not_found"]


def test_domain_resolver_normalizes_month_range_label() -> None:
    session = create_session()
    add_payment_article(session, "Rent office", 1, period_month=date(2026, 3, 1))
    add_payment_article(session, "Rent office", 2, period_month=date(2026, 4, 1))
    add_payment_article(session, "Rent office", 3, period_month=date(2026, 5, 1))
    session.commit()
    resolver = DomainResolver(session)

    resolution = resolver.resolve(build_period_label_frame("с марта по май"))

    assert resolution.valid is True
    assert resolution.frame.period.from_date == "2026-03-01"
    assert resolution.frame.period.to == "2026-05-31"
