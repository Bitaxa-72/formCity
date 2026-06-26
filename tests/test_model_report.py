from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, ModelComparisonFact, ModelKpiFact, ModelSource
from app.llm.answer import build_fallback_answer
from app.pipeline.calculation_engine import CalculationEngine
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics
from app.pipeline.response_data import build_response_data
from app.pipeline.result_verifier import verify_result
from app.pipeline.sql_compiler import compile_sql


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_model_source(session: Session, snapshot_month: date) -> None:
    session.add(
        ModelSource(
            project="obvodny",
            snapshot_month=snapshot_month,
            file_name=f"model_{snapshot_month.isoformat()}.xlsx",
            file_hash=f"hash_{snapshot_month.isoformat()}",
        ),
    )


def add_model_kpi(session: Session, snapshot_month: date, metric_name: str, metric_key: str, value: Decimal, row: int) -> None:
    session.add(
        ModelKpiFact(
            project="obvodny",
            snapshot_month=snapshot_month,
            scenario="current",
            section="KPI",
            metric_name=metric_name,
            metric_key=metric_key,
            value=value,
            normalized_value=value,
            unit="руб.",
            source_sheet="NEWKPI's_",
            source_row=row,
            source_col=6,
            source_file=f"model_{snapshot_month.isoformat()}.xlsx",
        ),
    )


def add_model_comparison(session: Session, snapshot_month: date, metric_name: str, metric_key: str, value: Decimal, row: int) -> None:
    session.add(
        ModelComparisonFact(
            project="obvodny",
            snapshot_month=snapshot_month,
            section="KPI",
            metric_name=metric_name,
            metric_key=metric_key,
            current_value=value,
            plan_value=None,
            deviation_value=None,
            deviation_percent=None,
            unit="руб.",
            source_sheet="Сравнение",
            source_row=row,
            source_file=f"model_{snapshot_month.isoformat()}.xlsx",
        ),
    )


def test_model_defaults_to_latest_snapshot_and_summary_metrics() -> None:
    session = create_session()
    add_model_source(session, date(2026, 3, 1))
    add_model_source(session, date(2026, 4, 1))
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
            },
        ),
    )
    result = DomainResolver(session).resolve(frame)

    assert result.valid is True
    assert result.frame.project == "obvodny"
    assert result.frame.period.from_date == "2026-04-01"
    assert result.frame.metrics == [
        "model_revenue",
        "model_cost_of_sales",
        "model_gross_profit",
        "model_net_profit",
        "model_npv",
    ]


def test_model_metric_query_uses_kpi_table() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_kpi(session, date(2026, 4, 1), "Выручка", "model_revenue", Decimal("1000"), 1)
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "metrics": ["model_revenue"],
            },
        ),
    )
    frame = DomainResolver(session).resolve(frame).frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)

    draft = build_fallback_answer(response_data)

    assert "model_kpi_facts" in query.table
    assert "model_comparison_facts" in query.table
    assert calculation.rows[0]["model_revenue"] == 1000.0
    assert "Модель" in draft.text
    assert "Выручка: 1 000 руб." in draft.text


def test_model_metric_query_uses_comparison_table() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_comparison(session, date(2026, 4, 1), "NPV", "model_npv", Decimal("500"), 1)
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "metrics": ["model_npv"],
            },
        ),
    )
    frame = DomainResolver(session).resolve(frame).frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)

    draft = build_fallback_answer(response_data)

    assert calculation.rows[0]["model_npv"] == 500.0
    assert "NPV: 500 руб." in draft.text


def test_model_metric_dimension_returns_available_metric_names() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_kpi(session, date(2026, 4, 1), "Выручка", "model_revenue", Decimal("1000"), 1)
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "view": "model_available_metrics",
            },
        ),
    )
    frame = DomainResolver(session).resolve(frame).frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)

    draft = build_fallback_answer(response_data)

    assert query.metrics == []
    assert query.group_by == ["metric"]
    assert "Показатели:" in draft.text
    assert "- Выручка" in draft.text
