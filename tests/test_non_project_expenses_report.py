from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, NonProjectExpenseFact, NonProjectExpenseSource
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


def add_source(session: Session, period_month: date) -> None:
    session.add(
        NonProjectExpenseSource(
            project="all",
            period_month=period_month,
            filled_at=period_month,
            file_name=f"non_project_{period_month.isoformat()}.xlsx",
            file_hash=f"hash_{period_month.isoformat()}",
        ),
    )


def add_fact(
    session: Session,
    period_month: date,
    row_order: int,
    row_type: str,
    item_kind: str,
    fm_category: str | None,
    item_name: str,
    amount: Decimal,
    executed_amount: Decimal,
    remaining_amount: Decimal,
) -> None:
    session.add(
        NonProjectExpenseFact(
            project="all",
            period_month=period_month,
            filled_at=period_month,
            row_order=row_order,
            row_type=row_type,
            item_kind=item_kind,
            fm_category=fm_category,
            item_name=item_name,
            amount=amount,
            executed_amount=executed_amount,
            remaining_amount=remaining_amount,
            unit="rub",
            is_sensitive=False,
            source_sheet="Лист1",
            source_row=row_order,
            source_file=f"non_project_{period_month.isoformat()}.xlsx",
        ),
    )


def execute_frame(session: Session, state: dict) -> tuple[object, object, object]:
    frame = apply_report_semantics(build_query_frame(state))
    domain_resolution = DomainResolver(session).resolve(frame)
    assert domain_resolution.valid is True
    frame = domain_resolution.frame
    metric_resolution = resolve_metrics(frame)
    assert metric_resolution.valid is True
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)
    return frame, calculation, build_fallback_answer(response_data)


def fill_non_project_expenses(session: Session) -> None:
    add_source(session, date(2026, 3, 1))
    add_source(session, date(2026, 4, 1))
    add_fact(
        session,
        date(2026, 3, 1),
        3,
        "detail",
        "commercial",
        "коммерческие расходы",
        "Реклама",
        Decimal("100"),
        Decimal("70"),
        Decimal("30"),
    )
    add_fact(
        session,
        date(2026, 4, 1),
        3,
        "detail",
        "commercial",
        "коммерческие расходы",
        "Реклама",
        Decimal("200"),
        Decimal("150"),
        Decimal("50"),
    )
    add_fact(
        session,
        date(2026, 4, 1),
        4,
        "summary",
        "non_project_expenses_total",
        None,
        "Непроектные расходы",
        Decimal("300"),
        Decimal("200"),
        Decimal("100"),
    )
    session.commit()


def test_non_project_expenses_defaults_to_latest_period_and_category_summary() -> None:
    session = create_session()
    fill_non_project_expenses(session)

    frame, calculation, draft = execute_frame(
        session,
        {
            "last_intent": "data_query",
            "report_type": "non_project_expenses",
        },
    )

    assert frame.project == "all"
    assert frame.period.from_date == "2026-04-01"
    assert frame.metrics == ["amount", "executed_amount", "remaining_amount"]
    assert frame.filters == {"row_type": "detail"}
    assert frame.group_by == ["fm_category"]
    assert calculation.rows[0]["amount"] == 200.0
    assert "Непроектные расходы" in draft.text
    assert "Период: последний актуальный месяц, апрель 2026" in draft.text
    assert "Сумма: 200 руб." in draft.text


def test_non_project_expenses_metric_query_filters_category() -> None:
    session = create_session()
    fill_non_project_expenses(session)

    frame, calculation, draft = execute_frame(
        session,
        {
            "last_intent": "data_query",
            "report_type": "non_project_expenses",
            "metrics": ["executed_amount"],
            "period": {"label": "март"},
            "filters": {"fm_category": "коммерческие"},
        },
    )

    assert frame.filters["fm_category"] == "коммерческие расходы"
    assert calculation.rows[0]["executed_amount"] == 70.0
    assert "Исполнено: 70 руб." in draft.text


def test_non_project_expenses_period_dimension_returns_periods() -> None:
    session = create_session()
    fill_non_project_expenses(session)

    frame, calculation, draft = execute_frame(
        session,
        {
            "last_intent": "data_query",
            "report_type": "non_project_expenses",
            "view": "non_project_expenses_available_periods",
        },
    )

    assert frame.intent == "dimension_query"
    assert frame.dimension == "period_month"
    assert calculation.rows == [{"period_month": "2026-03-01"}, {"period_month": "2026-04-01"}]
    assert "Периоды:" in draft.text
    assert "- март 2026" in draft.text
    assert "- апрель 2026" in draft.text


def test_non_project_expenses_compatibility_rejects_sales_metric() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "non_project_expenses",
                "metrics": ["amount"],
            },
        ),
    )

    result = check_report_compatibility(frame, "непроектные расходы выручка апрель")

    assert result.valid is False
    assert result.error == "metric_not_supported_for_non_project_expenses"
    assert result.message is not None
    assert 'нет показателя "выручка"' in result.message
