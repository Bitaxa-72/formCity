from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, SalesPlanExecutionFact, SalesPlanExecutionSource
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
from app.reports.sales_plan_execution.corrections import build_sales_plan_execution_correction


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def sales_plan_fact(
    snapshot_month: date,
    block_kind: str,
    segment: str,
    metric_key: str,
    scenario: str,
    value: Decimal,
    unit: str,
    owner_scope: str = "all",
    period_kind: str = "snapshot",
    period_month: date | None = None,
    year: int | None = None,
    source_row: int = 1,
    source_col: int = 1,
) -> SalesPlanExecutionFact:
    segment_labels = {
        "project_total": "Итого проект",
        "apartments": "Апартаменты",
        "restaurant": "Ресторан",
    }
    metric_names = {
        "sales_revenue": "Продажи",
        "cash_receipts": "Поступление денежных средств",
        "contract_area_sqm": "Объем законтрактованных площадей",
        "contract_count": "Объем законтрактованных площадей",
        "price_per_sqm": "Цена за 1 м2",
    }
    return SalesPlanExecutionFact(
        project="obvodny",
        snapshot_month=snapshot_month,
        snapshot_date=date(snapshot_month.year, snapshot_month.month, 28),
        block_kind=block_kind,
        block_label="Итого проект",
        segment=segment,
        segment_label=segment_labels[segment],
        metric_key=metric_key,
        metric_name=metric_names[metric_key],
        owner_scope=owner_scope,
        period_kind=period_kind,
        period_month=period_month or snapshot_month,
        year=year,
        scenario=scenario,
        value=value,
        unit=unit,
        source_sheet="Обводный 118",
        source_row=source_row,
        source_col=source_col,
        source_file=f"plan_{snapshot_month.isoformat()}.xlsx",
    )


def add_sales_plan_data(session: Session) -> None:
    for index, snapshot in enumerate([date(2026, 2, 1), date(2026, 4, 1)], start=1):
        session.add(
            SalesPlanExecutionSource(
                project="obvodny",
                snapshot_month=snapshot,
                snapshot_date=date(snapshot.year, snapshot.month, 28),
                file_name=f"Отчет об исполнении плана продаж_{snapshot.isoformat()}.xlsx",
                file_hash=f"hash-{index}",
            ),
        )

    session.add_all(
        [
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "sales_revenue", "plan", Decimal("1200"), "rub", source_row=1, source_col=4),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "sales_revenue", "fact", Decimal("900"), "rub", source_row=1, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "sales_revenue", "deviation", Decimal("-300"), "rub", source_row=1, source_col=6),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "cash_receipts", "plan", Decimal("1000"), "rub", source_row=2, source_col=4),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "cash_receipts", "fact", Decimal("800"), "rub", source_row=2, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "contract_area_sqm", "fact", Decimal("90"), "sqm", source_row=3, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "project_total", "contract_count", "fact", Decimal("9"), "count", source_row=4, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "apartments", "sales_revenue", "fact", Decimal("700"), "rub", source_row=5, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "apartments", "contract_area_sqm", "fact", Decimal("70"), "sqm", source_row=6, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "apartments", "contract_count", "fact", Decimal("7"), "count", source_row=7, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "apartments", "price_per_sqm", "fact", Decimal("10"), "rub_per_sqm", source_row=8, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "restaurant", "sales_revenue", "fact", Decimal("200"), "rub", source_row=9, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "restaurant", "contract_area_sqm", "fact", Decimal("20"), "sqm", source_row=10, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "restaurant", "contract_count", "fact", Decimal("2"), "count", source_row=11, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "segment_cumulative", "restaurant", "price_per_sqm", "fact", Decimal("10"), "rub_per_sqm", source_row=12, source_col=5),
            sales_plan_fact(date(2026, 4, 1), "year", "project_total", "sales_revenue", "remaining_to_sell", Decimal("300"), "rub", period_kind="year", period_month=None, year=2026, source_row=13, source_col=8),
            sales_plan_fact(date(2026, 2, 1), "segment_cumulative", "project_total", "sales_revenue", "fact", Decimal("500"), "rub", source_row=1, source_col=5),
        ],
    )
    session.commit()


def build_sales_plan_answer(session: Session, state: dict[str, object], text: str | None = None):
    frame = apply_report_semantics(build_query_frame(state))
    compatibility = check_report_compatibility(frame, text)
    if not compatibility.valid:
        return compatibility, None, None, None
    resolution = DomainResolver(session).resolve(frame)
    if not resolution.valid:
        return resolution, None, None, None
    frame = resolution.frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)
    return build_fallback_answer(response_data), calculation, query, frame


def test_sales_plan_summary_uses_latest_snapshot() -> None:
    session = create_session()
    add_sales_plan_data(session)

    draft, calculation, _query, frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_plan_execution",
            "view": "sales_plan_summary",
        },
    )

    assert frame.period.from_date == "2026-04-01"
    assert calculation.row_count == 3
    assert "Исполнение плана продаж" in draft.text
    assert "Сценарий: План" in draft.text
    assert "Продажи: 1 200 руб." in draft.text
    assert "Поступления денежных средств: 1 000 руб." in draft.text


def test_sales_plan_by_segments_returns_segment_breakdown() -> None:
    session = create_session()
    add_sales_plan_data(session)

    draft, calculation, _query, _frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_plan_execution",
            "view": "sales_plan_by_segments",
            "filters": {"scenario": "fact"},
        },
    )

    assert calculation.row_count == 2
    assert "Сегмент: Апартаменты" in draft.text
    assert "Сегмент: Ресторан" in draft.text
    assert "Продажи: 700 руб." in draft.text
    assert "Площадь контрактации: 70 м2" in draft.text


def test_sales_plan_available_snapshots_dimension() -> None:
    session = create_session()
    add_sales_plan_data(session)

    draft, calculation, _query, _frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "sales_plan_execution",
            "view": "sales_plan_available_snapshots",
            "dimension": "snapshot_month",
        },
    )

    assert calculation.row_count == 2
    assert "Срезы" in draft.text
    assert "- февраль 2026" in draft.text
    assert "- апрель 2026" in draft.text


def test_sales_plan_missing_snapshot_returns_clear_message() -> None:
    session = create_session()
    add_sales_plan_data(session)

    resolution, calculation, query, frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_plan_execution",
            "view": "sales_plan_summary",
            "period": {"label": "май 2026"},
        },
    )

    assert resolution.valid is False
    assert calculation is None
    assert query is None
    assert frame is None
    assert "За указанный срез исполнения плана продаж нет данных" in resolution.clarification_question


def test_sales_plan_wrong_project_uses_obvodny_with_notice() -> None:
    session = create_session()
    add_sales_plan_data(session)

    draft, _calculation, _query, _frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_plan_execution",
            "project": "moskovsky",
            "view": "sales_plan_summary",
        },
    )

    assert "загружен только по Обводному" in draft.text
    assert "Проект: Обводный" in draft.text


def test_sales_plan_unsupported_metric_is_blocked() -> None:
    session = create_session()
    add_sales_plan_data(session)

    compatibility, calculation, query, frame = build_sales_plan_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "sales_plan_execution",
            "view": "sales_plan_summary",
        },
        text="исполнение плана продаж факт по ФОТ",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert frame is None
    assert "нет показателя" in compatibility.message


def test_sales_plan_correction_recognizes_fact_revenue() -> None:
    parsed = build_sales_plan_execution_correction("исполнение плана продаж факт продажи апрель")

    assert parsed is not None
    assert parsed.state_delta.report_type == "sales_plan_execution"
    assert parsed.state_delta.project == "obvodny"
    assert parsed.state_delta.metrics == ["sales_plan_revenue"]
    assert parsed.state_delta.filters["scenario"] == "fact"
    assert parsed.state_delta.period.label == "апрель"
