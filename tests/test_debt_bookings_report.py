from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, DebtBookingDeviation, DebtBookingItem, DebtBookingMonthlyValue, DebtBookingRefusal, DebtBookingSource
from app.llm.answer import build_fallback_answer
from app.pipeline.calculation_engine import CalculationEngine
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_compatibility import check_report_compatibility
from app.pipeline.report_semantics import apply_report_semantics
from app.pipeline.response_data import build_response_data
from app.pipeline.result_verifier import verify_result
from app.pipeline.sql_compiler import compile_sql


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_debt_data(session: Session) -> None:
    session.add(
        DebtBookingSource(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            file_name="Отчет о ДЗ и Бронях_апрель 2026.xlsx",
            file_hash="hash",
        ),
    )
    session.add_all(
        [
            DebtBookingItem(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=1,
                row_type="category",
                item_kind="overdue",
                section="Просроченные",
                client_name="Просроченные",
                manager_name=None,
                is_special_client=False,
                unit_number=None,
                total_amount=Decimal("1000"),
                comments=None,
                contacts=None,
                unit="rub",
                is_sensitive=True,
                sensitive_fields={"client_name": True},
                source_sheet="ДЗ и Брони",
                source_row=1,
                source_file="source.xlsx",
            ),
            DebtBookingItem(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=2,
                row_type="detail",
                item_kind="booking",
                section="Брони",
                client_name="Иванов Иван",
                manager_name="Менеджер",
                is_special_client=False,
                unit_number="1.1",
                total_amount=Decimal("500"),
                comments="Комментарий",
                contacts="+79999999999",
                unit="rub",
                is_sensitive=True,
                sensitive_fields={"client_name": True, "contacts": True},
                source_sheet="ДЗ и Брони",
                source_row=2,
                source_file="source.xlsx",
            ),
        ],
    )
    session.add(
        DebtBookingMonthlyValue(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            item_source_row=2,
            item_kind="booking",
            row_type="detail",
            period_month=date(2026, 5, 1),
            value=Decimal("300"),
            unit="rub",
            source_sheet="ДЗ и Брони",
            source_row=2,
            source_col=11,
            source_file="source.xlsx",
        ),
    )
    session.add(
        DebtBookingDeviation(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            period_month=date(2026, 4, 1),
            row_order=1,
            row_type="detail",
            item_kind="booking",
            section="Брони",
            client_name="Иванов Иван",
            unit_number="1.1",
            plan_amount=Decimal("1000"),
            updated_plan_amount=Decimal("1200"),
            plan_comment="План",
            fact_payment_amount=Decimal("800"),
            remaining_amount=Decimal("400"),
            fact_comment="Факт",
            unit="rub",
            is_sensitive=True,
            sensitive_fields={"client_name": True, "unit_number": True},
            source_sheet="Отклонения",
            source_row=1,
            source_file="source.xlsx",
        ),
    )
    session.add(
        DebtBookingRefusal(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            row_order=1,
            customer_name="Петров Петр",
            status="Отказ",
            area_sqm=Decimal("42.5"),
            unit_number="2.1",
            full_price_amount=Decimal("12000000"),
            payment_type="ипотека",
            reason="Причина",
            agency="Агентство",
            manager_name="Менеджер",
            unit="rub",
            is_sensitive=True,
            sensitive_fields={"customer_name": True, "reason": True},
            source_sheet="Отказы",
            source_row=1,
            source_file="source.xlsx",
        ),
    )
    session.commit()


def build_debt_answer(session: Session, state: dict[str, object], text: str | None = None):
    frame = apply_report_semantics(build_query_frame(state))
    compatibility = check_report_compatibility(frame, text)
    if not compatibility.valid:
        return compatibility, None, None
    frame = DomainResolver(session).resolve(frame).frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)
    return build_fallback_answer(response_data), calculation, query


def test_debt_bookings_summary_returns_safe_aggregates() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, query = build_debt_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_summary",
            "metrics": ["debt_item_count", "debt_total_amount"],
        },
    )

    assert query.table.startswith("(")
    assert calculation.row_count == 2
    assert "Брони" in draft.text
    assert "Просроченные" in draft.text
    assert "Иванов" not in draft.text
    assert "+79999999999" not in draft.text


def test_debt_bookings_deviations_returns_plan_fact_remaining() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_deviations",
        },
    )

    assert calculation.row_count == 1
    assert "План: 1 000 руб." in draft.text
    assert "Уточненный план: 1 200 руб." in draft.text
    assert "Факт оплат: 800 руб." in draft.text
    assert "Остаток: 400 руб." in draft.text
    assert "Иванов" not in draft.text


def test_debt_bookings_refusals_returns_safe_aggregates() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_refusals",
        },
    )

    assert calculation.row_count == 1
    assert "Количество отказов: 1" in draft.text
    assert "Площадь отказов: 42.5 м2" in draft.text
    assert "Сумма отказов: 12 000 000 руб." in draft.text
    assert "Петров" not in draft.text
    assert "Причина" not in draft.text


def test_debt_bookings_period_dimension_returns_snapshots() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_available_periods",
            "dimension": "snapshot_month",
        },
    )

    assert calculation.row_count == 1
    assert "Срезы:" in draft.text
    assert "- апрель 2026" in draft.text


def test_debt_bookings_unit_number_dimension_returns_room_numbers() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_available_unit_numbers",
            "dimension": "unit_number",
        },
    )

    assert calculation.row_count == 2
    assert "Номера помещений:" in draft.text
    assert "- 1.1" in draft.text
    assert "- 2.1" in draft.text
    assert "Иванов" not in draft.text
    assert "Петров" not in draft.text


def test_debt_bookings_group_by_unit_number_returns_safe_aggregates() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_summary",
            "metrics": ["debt_item_count", "debt_total_amount"],
            "group_by": ["unit_number"],
        },
    )

    assert calculation.row_count == 1
    assert "Номер помещения: 1.1" in draft.text
    assert "Количество строк: 1" in draft.text
    assert "Сумма: 500 руб." in draft.text
    assert "Иванов" not in draft.text


def test_debt_bookings_unit_number_request_is_allowed() -> None:
    session = create_session()
    add_debt_data(session)

    draft, calculation, _query = build_debt_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_available_unit_numbers",
            "dimension": "unit_number",
        },
        text="ДЗ и брони номера помещений",
    )

    assert calculation.row_count == 2
    assert "Номера помещений:" in draft.text


def test_debt_bookings_sensitive_request_is_blocked() -> None:
    session = create_session()
    add_debt_data(session)

    compatibility, calculation, query = build_debt_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "debt_and_bookings",
            "view": "debt_bookings_summary",
            "metrics": ["debt_item_count"],
        },
        text="ДЗ и брони покажи клиентов и контакты",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert "не вывожу" in compatibility.message
