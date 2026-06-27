from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, StockForSaleFact, StockForSaleSource
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
from app.reports.stock_for_sale.corrections import build_stock_for_sale_correction


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_stock_data(session: Session) -> None:
    session.add(
        StockForSaleSource(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            file_name="Остатки в продаже_30.04.2026.xlsx",
            file_hash="hash",
        ),
    )
    session.add_all(
        [
            StockForSaleFact(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=1,
                row_type="total",
                row_label="Всего",
                property_type="total",
                floor_number=None,
                is_in_work=False,
                ddu_amount=Decimal("1000"),
                dupt_markup_amount=Decimal("200"),
                total_amount=Decimal("1200"),
                area_sqm=Decimal("10"),
                unit_count=2,
                ddu_price_per_sqm=Decimal("100"),
                dupt_price_per_sqm=Decimal("20"),
                total_price_per_sqm=Decimal("120"),
                unit="mixed",
                source_sheet="Остатки в продаже",
                source_row=1,
                source_file="source.xlsx",
            ),
            StockForSaleFact(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=2,
                row_type="category",
                row_label="апартаменты",
                property_type="apartment",
                floor_number=None,
                is_in_work=False,
                ddu_amount=Decimal("800"),
                dupt_markup_amount=Decimal("160"),
                total_amount=Decimal("960"),
                area_sqm=Decimal("8"),
                unit_count=1,
                ddu_price_per_sqm=Decimal("100"),
                dupt_price_per_sqm=Decimal("20"),
                total_price_per_sqm=Decimal("120"),
                unit="mixed",
                source_sheet="Остатки в продаже",
                source_row=2,
                source_file="source.xlsx",
            ),
            StockForSaleFact(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=3,
                row_type="detail",
                row_label="1 этаж",
                property_type="first_floor",
                floor_number=1,
                is_in_work=False,
                ddu_amount=Decimal("500"),
                dupt_markup_amount=Decimal("100"),
                total_amount=Decimal("600"),
                area_sqm=Decimal("5"),
                unit_count=1,
                ddu_price_per_sqm=Decimal("100"),
                dupt_price_per_sqm=Decimal("20"),
                total_price_per_sqm=Decimal("120"),
                unit="mixed",
                source_sheet="Остатки в продаже",
                source_row=3,
                source_file="source.xlsx",
            ),
            StockForSaleFact(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=4,
                row_type="detail",
                row_label="1 этаж в работе",
                property_type="first_floor",
                floor_number=1,
                is_in_work=True,
                ddu_amount=Decimal("200"),
                dupt_markup_amount=Decimal("40"),
                total_amount=Decimal("240"),
                area_sqm=Decimal("2"),
                unit_count=1,
                ddu_price_per_sqm=Decimal("100"),
                dupt_price_per_sqm=Decimal("20"),
                total_price_per_sqm=Decimal("120"),
                unit="mixed",
                source_sheet="Остатки в продаже",
                source_row=4,
                source_file="source.xlsx",
            ),
        ],
    )
    session.commit()


def build_stock_answer(session: Session, state: dict[str, object], text: str | None = None):
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


def test_stock_summary_uses_total_row_only() -> None:
    session = create_session()
    add_stock_data(session)

    draft, calculation, _query = build_stock_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "stock_for_sale",
            "view": "stock_summary",
        },
    )

    assert calculation.row_count == 1
    assert "Остатки в продаже" in draft.text
    assert "Сумма всего: 1 200 руб." in draft.text
    assert "Площадь: 10 м2" in draft.text
    assert "Количество объектов: 2" in draft.text
    assert "Цена за м2: 120 руб./м2" in draft.text


def test_stock_by_floors_returns_floor_breakdown() -> None:
    session = create_session()
    add_stock_data(session)

    draft, calculation, _query = build_stock_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "stock_for_sale",
            "view": "stock_by_floors",
        },
    )

    assert calculation.row_count == 1
    assert "Этаж: 1" in draft.text
    assert "Сумма всего: 840 руб." in draft.text


def test_stock_period_dimension_returns_snapshots() -> None:
    session = create_session()
    add_stock_data(session)

    draft, calculation, _query = build_stock_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "stock_for_sale",
            "view": "stock_available_periods",
            "dimension": "snapshot_month",
        },
    )

    assert calculation.row_count == 1
    assert "Срезы:" in draft.text
    assert "- апрель 2026" in draft.text


def test_stock_wrong_project_uses_obvodny_with_notice() -> None:
    session = create_session()
    add_stock_data(session)

    draft, _calculation, _query = build_stock_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "stock_for_sale",
            "project": "moskovsky",
            "view": "stock_summary",
        },
    )

    assert "Остатки в продаже сейчас загружены только по Обводному" in draft.text
    assert "Проект: Обводный" in draft.text


def test_stock_sensitive_request_is_blocked() -> None:
    session = create_session()
    add_stock_data(session)

    compatibility, calculation, query = build_stock_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "stock_for_sale",
            "view": "stock_summary",
        },
        text="остатки в продаже покажи покупателей и контакты",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert "не вывожу" in compatibility.message


def test_stock_correction_recognizes_price_per_sqm() -> None:
    parsed = build_stock_for_sale_correction("остатки в продаже цена за метр апрель")

    assert parsed is not None
    assert parsed.state_delta.report_type == "stock_for_sale"
    assert parsed.state_delta.view == "stock_price_per_sqm"
    assert parsed.state_delta.period.label == "апрель"
