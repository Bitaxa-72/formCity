from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, SalesReportFact, SalesReportSource
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
from app.reports.sales_report.corrections import build_sales_report_correction


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def sales_fact(
    segment: str,
    metric_key: str,
    value: Decimal,
    unit: str,
    period_kind: str = "total",
    period_month: date | None = None,
    scenario: str = "total",
    owner_scope: str = "all",
) -> SalesReportFact:
    segment_labels = {
        "project_total": "Итого по проекту",
        "apartments": "Апартаменты",
        "storage": "Кладовки",
    }
    metric_names = {
        "contract_revenue": "Выручка по контрактации",
        "contract_area_sqm": "Объем контрактации, кв.м.",
        "contract_count": "Объем контрактации, шт.",
        "price_per_sqm": "Цена за 1 кв.м.",
        "ddu_actual_payments": "Фактические оплаты по ДДУ",
        "ddu_remaining_payment_schedule": "График оплаты остатка по ДДУ",
    }
    return SalesReportFact(
        project="obvodny",
        snapshot_month=date(2026, 4, 1),
        snapshot_date=date(2026, 4, 30),
        segment=segment,
        segment_label=segment_labels[segment],
        metric_key=metric_key,
        metric_name=metric_names[metric_key],
        owner_scope=owner_scope,
        period_kind=period_kind,
        period_month=period_month,
        scenario=scenario,
        value=value,
        unit=unit,
        source_sheet="Лист1",
        source_row=1,
        source_col=3 if period_kind == "total" else (4 if scenario == "fact" else 5),
        source_file="source.xlsx",
    )


def add_sales_data(session: Session) -> None:
    session.add(
        SalesReportSource(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            file_name="Отчет о продажах.xlsx",
            file_hash="hash",
        ),
    )
    session.add_all(
        [
            sales_fact("project_total", "contract_revenue", Decimal("1000"), "thousand_rub"),
            sales_fact("project_total", "ddu_actual_payments", Decimal("800"), "thousand_rub"),
            sales_fact("project_total", "ddu_remaining_payment_schedule", Decimal("200"), "thousand_rub"),
            sales_fact("apartments", "contract_revenue", Decimal("700"), "thousand_rub"),
            sales_fact("apartments", "contract_area_sqm", Decimal("70"), "sqm"),
            sales_fact("apartments", "contract_count", Decimal("7"), "count"),
            sales_fact("apartments", "price_per_sqm", Decimal("10"), "thousand_rub_per_sqm"),
            sales_fact("storage", "contract_revenue", Decimal("300"), "thousand_rub"),
            sales_fact("storage", "contract_area_sqm", Decimal("30"), "sqm"),
            sales_fact("storage", "contract_count", Decimal("3"), "count"),
            sales_fact("storage", "price_per_sqm", Decimal("10"), "thousand_rub_per_sqm"),
            sales_fact("project_total", "contract_revenue", Decimal("90"), "thousand_rub", period_kind="month", period_month=date(2026, 3, 1), scenario="fact"),
            sales_fact("project_total", "contract_revenue", Decimal("110"), "thousand_rub", period_kind="month", period_month=date(2026, 3, 1), scenario="plan"),
        ],
    )
    session.commit()


def build_sales_answer(session: Session, state: dict[str, object], text: str | None = None):
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


def test_sales_summary_uses_project_total() -> None:
    session = create_session()
    add_sales_data(session)

    draft, calculation, _query = build_sales_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "view": "sales_summary",
        },
    )

    assert calculation.row_count == 1
    assert "Отчет о продажах" in draft.text
    assert "Выручка по контрактации: 1 000 тыс. руб." in draft.text
    assert "Фактические оплаты по ДДУ: 800 тыс. руб." in draft.text
    assert "График оплаты остатка по ДДУ: 200 тыс. руб." in draft.text


def test_sales_by_segments_returns_segment_breakdown() -> None:
    session = create_session()
    add_sales_data(session)

    draft, calculation, _query = build_sales_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "view": "sales_by_segments",
        },
    )

    assert calculation.row_count == 2
    assert "Сегмент: Апартаменты" in draft.text
    assert "Сегмент: Кладовки" in draft.text
    assert "Объем контрактации: 70 м2" in draft.text
    assert "Количество сделок: 7" in draft.text


def test_sales_month_filter_groups_fact_and_plan() -> None:
    session = create_session()
    add_sales_data(session)

    draft, calculation, _query = build_sales_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "metrics": ["sales_contract_revenue"],
            "filters": {"period_month": "2026-03-01"},
        },
    )

    assert calculation.row_count == 2
    assert "Сценарий: Факт" in draft.text
    assert "Сценарий: План" in draft.text
    assert "90 тыс. руб." in draft.text
    assert "110 тыс. руб." in draft.text


def test_sales_available_periods_dimension() -> None:
    session = create_session()
    add_sales_data(session)

    draft, calculation, _query = build_sales_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "sales_report",
            "view": "sales_available_periods",
            "dimension": "period_month",
        },
    )

    assert calculation.row_count == 1
    assert "Периоды:" in draft.text
    assert "- март 2026" in draft.text


def test_sales_wrong_project_uses_obvodny_with_notice() -> None:
    session = create_session()
    add_sales_data(session)

    draft, _calculation, _query = build_sales_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "project": "moskovsky",
            "view": "sales_summary",
        },
    )

    assert "Отчет о продажах сейчас загружен только по Обводному" in draft.text
    assert "Проект: Обводный" in draft.text


def test_sales_sensitive_request_is_blocked() -> None:
    session = create_session()
    add_sales_data(session)

    compatibility, calculation, query = build_sales_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_report",
            "view": "sales_summary",
        },
        text="отчет о продажах покажи клиентов и телефоны",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert "не вывожу" in compatibility.message


def test_sales_correction_recognizes_revenue_month() -> None:
    parsed = build_sales_report_correction("отчет о продажах выручка за март")

    assert parsed is not None
    assert parsed.state_delta.report_type == "sales_report"
    assert parsed.state_delta.metrics == ["sales_contract_revenue"]
    assert parsed.state_delta.filters["period_month"] == "2026-03-01"
