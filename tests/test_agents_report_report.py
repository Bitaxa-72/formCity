from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import AgentsReportDeal, AgentsReportMonthlyValue, AgentsReportSource, Base
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
from app.reports.agents_report.corrections import build_agents_report_correction


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_agents_data(session: Session) -> None:
    session.add(
        AgentsReportSource(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            snapshot_date=date(2026, 4, 30),
            file_name="Отчет по агентам.xlsx",
            file_hash="hash",
        ),
    )
    session.add_all(
        [
            AgentsReportDeal(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=1,
                agent_name="Иванов Иван",
                unit_number="1.1",
                buyer_name="Петров Петр",
                ddu_number="ДДУ-123",
                contract_date=date(2026, 3, 1),
                area_sqm=Decimal("50"),
                commission_base_amount=Decimal("10000000"),
                check_qw_amount=Decimal("10000000"),
                check_gh_amount=Decimal("0"),
                commission_rate=Decimal("0.03"),
                commission_amount=Decimal("300000"),
                act_total_amount=Decimal("300000"),
                paid_amount=Decimal("100000"),
                remaining_amount=Decimal("200000"),
                act_info="Акт 77",
                budget_month=date(2026, 4, 1),
                ddu_assignment_amount=Decimal("12000000"),
                ddu_assignment_price_per_sqm=Decimal("240000"),
                ddu_amount=Decimal("10000000"),
                ddu_price_per_sqm=Decimal("200000"),
                assignment_amount=Decimal("2000000"),
                assignment_price_per_sqm=Decimal("40000"),
                furniture_amount=Decimal("500000"),
                note="секретное примечание",
                unit="rub",
                is_sensitive=True,
                sensitive_fields={"agent_name": True, "buyer_name": True, "ddu_number": True, "act_info": True},
                source_sheet="Агенты",
                source_row=1,
                source_file="source.xlsx",
            ),
            AgentsReportDeal(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                row_order=2,
                agent_name="Сидоров Семен",
                unit_number="1.2",
                buyer_name="Клиент",
                ddu_number="ДДУ-456",
                contract_date=date(2026, 3, 2),
                area_sqm=Decimal("40"),
                commission_base_amount=Decimal("8000000"),
                check_qw_amount=Decimal("8000000"),
                check_gh_amount=Decimal("0"),
                commission_rate=Decimal("0.03"),
                commission_amount=Decimal("240000"),
                act_total_amount=Decimal("240000"),
                paid_amount=Decimal("240000"),
                remaining_amount=Decimal("0"),
                act_info="Акт 88",
                budget_month=date(2026, 5, 1),
                ddu_assignment_amount=Decimal("9000000"),
                ddu_assignment_price_per_sqm=Decimal("225000"),
                ddu_amount=Decimal("8000000"),
                ddu_price_per_sqm=Decimal("200000"),
                assignment_amount=Decimal("1000000"),
                assignment_price_per_sqm=Decimal("25000"),
                furniture_amount=Decimal("400000"),
                note=None,
                unit="rub",
                is_sensitive=True,
                sensitive_fields={"agent_name": True, "buyer_name": True, "ddu_number": True, "act_info": True},
                source_sheet="Агенты",
                source_row=2,
                source_file="source.xlsx",
            ),
        ],
    )
    session.add_all(
        [
            AgentsReportMonthlyValue(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                deal_source_row=1,
                value_kind="ddu_schedule",
                period_kind="month",
                period_month=date(2026, 6, 1),
                value=Decimal("7000000"),
                unit="rub",
                source_sheet="Агенты",
                source_row=1,
                source_col=10,
                source_file="source.xlsx",
            ),
            AgentsReportMonthlyValue(
                project="obvodny",
                snapshot_month=date(2026, 4, 1),
                snapshot_date=date(2026, 4, 30),
                deal_source_row=1,
                value_kind="assignment_schedule",
                period_kind="past_periods_total",
                period_month=None,
                value=Decimal("2000000"),
                unit="rub",
                source_sheet="Агенты",
                source_row=1,
                source_col=11,
                source_file="source.xlsx",
            ),
        ],
    )
    session.commit()


def build_agents_answer(session: Session, state: dict[str, object], text: str | None = None):
    frame = apply_report_semantics(build_query_frame(state))
    compatibility = check_report_compatibility(frame, text)
    if not compatibility.valid:
        return compatibility, None, None
    resolution = DomainResolver(session).resolve(frame)
    if not resolution.valid:
        return resolution, None, None
    frame = resolution.frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)
    return build_fallback_answer(response_data), calculation, query


def test_agents_summary_returns_safe_aggregates() -> None:
    session = create_session()
    add_agents_data(session)

    draft, calculation, _query = build_agents_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "agents_report",
            "view": "agents_summary",
        },
    )

    assert calculation.row_count == 1
    assert "Отчет по агентам" in draft.text
    assert "Количество сделок: 2" in draft.text
    assert "Агентское вознаграждение: 540 000 руб." in draft.text
    assert "Оплачено: 340 000 руб." in draft.text
    assert "Остаток к оплате: 200 000 руб." in draft.text
    assert "Иванов" not in draft.text
    assert "Петров" not in draft.text
    assert "ДДУ-123" not in draft.text
    assert "Акт 77" not in draft.text


def test_agents_ddu_view_returns_safe_amounts() -> None:
    session = create_session()
    add_agents_data(session)

    draft, calculation, _query = build_agents_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "agents_report",
            "view": "agents_ddu",
        },
    )

    assert calculation.row_count == 1
    assert "ДДУ + уступка: 21 000 000 руб." in draft.text
    assert "ДДУ: 18 000 000 руб." in draft.text
    assert "Уступка: 3 000 000 руб." in draft.text
    assert "Меблировка: 900 000 руб." in draft.text


def test_agents_monthly_view_uses_payment_month_without_period_warning() -> None:
    session = create_session()
    add_agents_data(session)

    draft, calculation, _query = build_agents_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "agents_report",
            "view": "agents_monthly",
        },
    )

    assert calculation.row_count == 2
    assert "Месяц оплаты: июнь 2026, График: График ДДУ" in draft.text
    assert "График: График уступки" in draft.text
    assert "Сумма графика: 7 000 000 руб." in draft.text
    assert "period_out_of_range" not in draft.text


def test_agents_available_snapshots_dimension() -> None:
    session = create_session()
    add_agents_data(session)

    draft, calculation, _query = build_agents_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "agents_report",
            "view": "agents_available_snapshots",
            "dimension": "snapshot_month",
        },
    )

    assert calculation.row_count == 1
    assert "Срезы:" in draft.text
    assert "- апрель 2026" in draft.text


def test_agents_wrong_project_uses_obvodny_with_notice() -> None:
    session = create_session()
    add_agents_data(session)

    draft, calculation, query = build_agents_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "agents_report",
            "project": "moskovsky",
            "view": "agents_summary",
        },
    )

    assert calculation.row_count == 1
    assert query is not None
    assert "Отчет по агентам сейчас загружен только по Обводному" in draft.text
    assert "Проект: Обводный" in draft.text


def test_agents_sensitive_request_is_blocked() -> None:
    session = create_session()
    add_agents_data(session)

    compatibility, calculation, query = build_agents_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "agents_report",
            "view": "agents_summary",
        },
        text="покажи список агентов и номера ДДУ",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert "не вывожу" in compatibility.message
    assert "список агентов" in compatibility.message


def test_agents_correction_recognizes_monthly_report() -> None:
    parsed = build_agents_report_correction("отчет по агентам помесячно апрель")

    assert parsed is not None
    assert parsed.state_delta.report_type == "agents_report"
    assert parsed.state_delta.view == "agents_monthly"
    assert parsed.state_delta.metrics == ["agents_monthly_value"]
    assert parsed.state_delta.period.label == "апрель"
