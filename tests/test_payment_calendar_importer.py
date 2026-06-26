from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.importers.payment_calendar import (
    build_payment_calendar_rows,
    classify_article,
    excel_serial_to_month,
    replace_payment_calendar_rows,
)
from app.db.models import Base, PaymentCalendarFact


def test_excel_serial_to_month_returns_first_day() -> None:
    assert excel_serial_to_month("46082") == date(2026, 3, 1)


def test_build_payment_calendar_rows_reads_articles_and_amounts() -> None:
    rows = {
        2: {3: "46082"},
        3: {3: "ПЛАН", 4: "ФАКТ", 5: "Отклонение ФАКТ-ПЛАН"},
        4: {2: "Поступления", 3: "1000", 4: "900", 5: "-100"},
        5: {2: "", 3: "50"},
        6: {2: "ИТОГО платежи", 3: "200,50", 4: "300.25", 5: "99.75"},
    }

    result = build_payment_calendar_rows(rows, project="moskovsky", source_file="file.xlsx")

    assert len(result) == 2
    assert result[0].period_month == date(2026, 3, 1)
    assert result[0].article == "Поступления"
    assert result[0].plan_amount == Decimal("1000")
    assert result[0].fact_amount == Decimal("900")
    assert result[0].deviation_amount == Decimal("-100")
    assert result[1].article == "ИТОГО платежи"
    assert result[1].plan_amount == Decimal("200.50")


def test_build_payment_calendar_rows_reads_shifted_amount_columns() -> None:
    rows = {
        2: {4: "46082"},
        3: {4: "ПЛАН", 5: "ФАКТ", 6: "Отклонение ФАКТ-ПЛАН"},
        4: {2: "Поступления", 4: "1000", 5: "900", 6: "-100"},
    }

    result = build_payment_calendar_rows(rows, project="obvodny", source_file="file.xlsx")

    assert len(result) == 1
    assert result[0].period_month == date(2026, 3, 1)
    assert result[0].article == "Поступления"
    assert result[0].plan_amount == Decimal("1000")
    assert result[0].fact_amount == Decimal("900")
    assert result[0].deviation_amount == Decimal("-100")


def test_classify_article_detects_service_rows() -> None:
    assert classify_article("ИТОГО платежи") == "payment_total"
    assert classify_article("Поступления") == "income_total"
    assert classify_article("Поступления от ДУПТ") == "income_total"
    assert classify_article("Остаток ДС на начало месяца") == "balance_start"
    assert classify_article("Остаток ДС на конец месяца") == "balance_end"
    assert classify_article("ООО Ромашка") == "detail"


def test_replace_payment_calendar_rows_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    rows = build_payment_calendar_rows(
        {
            2: {3: "46082"},
            4: {2: "Поступления", 3: "1000", 4: "900", 5: "-100"},
        },
        project="moskovsky",
        source_file="file.xlsx",
    )

    with session_factory() as session:
        assert replace_payment_calendar_rows(session, rows) == 1
        assert replace_payment_calendar_rows(session, rows) == 1
        stored = session.execute(select(PaymentCalendarFact)).scalars().all()

    assert len(stored) == 1
    assert stored[0].project == "moskovsky"
    assert stored[0].article == "Поступления"
    assert stored[0].article_kind == "income_total"
