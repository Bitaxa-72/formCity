from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, RoadmapStep
from app.llm.answer import build_fallback_answer
from app.pipeline.calculation_engine import CalculationEngine
from app.pipeline.domain_resolver import DomainResolver
from app.pipeline.metric_resolver import resolve_metrics
from app.pipeline.query_frame import build_query_frame
from app.pipeline.report_semantics import apply_report_semantics
from app.pipeline.response_data import build_response_data
from app.pipeline.result_verifier import verify_result
from app.pipeline.sql_compiler import compile_sql


def create_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return session_factory()


def add_roadmap_step(
    session,
    period_month: date,
    row_order: int,
    action_text: str,
    step_no: int | None = None,
    min_work_days: int | None = 1,
    max_work_days: int | None = 1,
    is_external: bool = False,
    is_total: bool = False,
) -> None:
    session.add(
        RoadmapStep(
            project="all",
            period_month=period_month,
            row_order=row_order,
            step_no=step_no,
            action_text=action_text,
            min_work_days=min_work_days,
            max_work_days=max_work_days,
            is_external=is_external,
            is_total=is_total,
            source_file="roadmap.xlsx",
        ),
    )


def test_roadmap_defaults_to_full_view() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
            },
        ),
    )

    assert frame.ready is True
    assert frame.project == "all"
    assert frame.view == "full_roadmap"
    assert frame.metrics == ["duration_min", "duration_max"]
    assert frame.group_by == ["row_order", "step", "parent_step", "action", "external", "total"]


def test_roadmap_total_duration_view_filters_total_row() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
                "view": "total_duration",
            },
        ),
    )

    assert frame.metrics == ["duration_min", "duration_max"]
    assert frame.filters == {"is_total": True}
    assert frame.group_by == []


def test_roadmap_domain_uses_latest_period_when_missing() -> None:
    session = create_session()
    add_roadmap_step(session, date(2026, 3, 1), 1, "March step", step_no=1)
    add_roadmap_step(session, date(2026, 4, 1), 1, "April step", step_no=1)
    session.commit()
    resolver = DomainResolver(session)
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
            },
        ),
    )

    result = resolver.resolve(frame)

    assert result.valid is True
    assert result.frame.period.from_date == "2026-04-01"
    assert result.frame.period.to == "2026-04-30"
    assert "последний актуальный месяц" in (result.frame.period.label or "")


def test_roadmap_period_dimension_keeps_all_periods() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "dimension_query",
                "report_type": "roadmap",
                "dimension": "period_month",
            },
        ),
    )
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)

    assert query.table == "roadmap_steps"
    assert query.metrics == []
    assert query.group_by == ["period_month"]
    assert "SELECT DISTINCT" in query.sql
    assert "period_month AS period_month" in query.sql


def test_roadmap_external_steps_can_filter_bank_text() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
                "view": "external_steps",
                "filters": {"action_text_contains": "БАНК"},
            },
        ),
    )
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)

    assert query.params["filter_action_text_contains"] == "%БАНК%"
    assert "action_text LIKE :filter_action_text_contains" in query.sql


def test_roadmap_full_answer_prints_steps_and_total() -> None:
    session = create_session()
    add_roadmap_step(session, date(2026, 4, 1), 1, "Prepare documents", step_no=1, min_work_days=1, max_work_days=1)
    add_roadmap_step(session, date(2026, 4, 1), 2, "Bank review", step_no=2, min_work_days=1, max_work_days=3, is_external=True)
    add_roadmap_step(session, date(2026, 4, 1), 3, "Итого в рабочих днях", min_work_days=9, max_work_days=15, is_total=True)
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
                "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель 2026"},
            },
        ),
    )
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)

    draft = build_fallback_answer(response_data)

    assert "Дорожная карта" in draft.text
    assert "Период: апрель 2026" in draft.text
    assert "1. Prepare documents" in draft.text
    assert "2. Bank review" in draft.text
    assert "Срок: 1-3 раб. дн." in draft.text
    assert "Итого: 9-15 раб. дн." in draft.text


def test_roadmap_total_duration_answer() -> None:
    session = create_session()
    add_roadmap_step(session, date(2026, 4, 1), 1, "Итого в рабочих днях", min_work_days=9, max_work_days=15, is_total=True)
    session.commit()

    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "roadmap",
                "view": "total_duration",
                "period": {"from": "2026-04-01", "to": "2026-04-30", "label": "апрель 2026"},
            },
        ),
    )
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)

    draft = build_fallback_answer(response_data)

    assert draft.text == "Дорожная карта\nПериод: апрель 2026\n\nИтого: 9-15 раб. дн."
