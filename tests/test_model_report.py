from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, ModelComparisonFact, ModelKpiFact, ModelRawCell, ModelRawRow, ModelRawSheet, ModelSource
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


def add_model_raw_sheet(session: Session, snapshot_month: date, sheet_name: str, sheet_kind: str, rows: int, cells: int) -> None:
    session.add(
        ModelRawSheet(
            project="obvodny",
            snapshot_month=snapshot_month,
            source_file=f"model_{snapshot_month.isoformat()}.xlsx",
            sheet_name=sheet_name,
            sheet_kind=sheet_kind,
            max_row=rows,
            max_column=10,
            row_count=rows,
            cell_count=cells,
        ),
    )


def add_model_raw_row(
    session: Session,
    snapshot_month: date,
    sheet_name: str,
    sheet_kind: str,
    row_number: int,
    row_label: str,
    values: list[tuple[int, str, str | None, Decimal | None, bool]],
) -> None:
    source_file = f"model_{snapshot_month.isoformat()}.xlsx"
    session.add(
        ModelRawRow(
            project="obvodny",
            snapshot_month=snapshot_month,
            source_file=source_file,
            sheet_name=sheet_name,
            sheet_kind=sheet_kind,
            row_number=row_number,
            row_label=row_label,
            non_empty_cells=len(values),
            raw_values={},
            is_sensitive=False,
            sensitive_kind=None,
        ),
    )
    for column_number, column_letter, value_text, value_number, is_sensitive in values:
        session.add(
            ModelRawCell(
                project="obvodny",
                snapshot_month=snapshot_month,
                source_file=source_file,
                sheet_name=sheet_name,
                sheet_kind=sheet_kind,
                row_number=row_number,
                column_number=column_number,
                column_letter=column_letter,
                value_type="number" if value_number is not None else "text",
                value_text=value_text,
                value_number=value_number,
                value_date=None,
                value_bool=None,
                is_sensitive=is_sensitive,
                sensitive_kind="contact" if is_sensitive else None,
            ),
        )


def build_model_answer(session: Session, state: dict[str, object]):
    frame = apply_report_semantics(build_query_frame(state))
    frame = DomainResolver(session).resolve(frame).frame
    metric_resolution = resolve_metrics(frame)
    query = compile_sql(frame, metric_resolution)
    calculation = CalculationEngine(session).calculate(frame, query, None)
    verification = verify_result(frame, metric_resolution, calculation)
    response_data = build_response_data(calculation, verification)
    return build_fallback_answer(response_data), calculation, query


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


def test_model_uses_obvodny_with_notice_for_other_project() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_comparison(session, date(2026, 4, 1), "NPV", "model_npv", Decimal("500"), 1)
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "model",
            "project": "moskovsky",
            "period": {"label": "апрель"},
            "metrics": ["model_npv"],
        },
    )

    assert query.params["project"] == "obvodny"
    assert calculation.rows[0]["model_npv"] == 500.0
    assert "Проект: Обводный" in draft.text
    assert "Финансовая модель сейчас загружена только по Обводному" in draft.text
    assert "вместо Московского" in draft.text
    assert "NPV: 500 руб." in draft.text


def test_model_all_project_does_not_show_instead_of_all_projects_notice() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_kpi(session, date(2026, 4, 1), "Общая площадь", "model_total_area", Decimal("56279.3"), 1)
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "model",
            "project": "all",
            "period": {"label": "апрель"},
            "metrics": ["model_total_area"],
            "view": "model_kpi",
        },
    )

    assert query.params["project"] == "obvodny"
    assert calculation.rows[0]["model_total_area"] == 56279.3
    assert "Общая площадь: 56 279.3 м2" in draft.text
    assert "вместо всех проектов" not in draft.text


def test_model_rejects_payment_calendar_metric_aliases() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "period": {"label": "апрель"},
                "metrics": [],
            },
        ),
    )

    check = check_report_compatibility(frame, "модель факт по ФОТ")

    assert check.valid is False
    assert check.error == "metric_not_supported_for_model"
    assert 'Показатель "факт"' in check.message


def test_model_rejects_sales_metric_aliases() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "period": {"label": "апрель"},
                "metrics": [],
            },
        ),
    )

    deal_check = check_report_compatibility(frame, "модель сделки за апрель")
    price_check = check_report_compatibility(frame, "модель цена метра за апрель")

    assert deal_check.valid is False
    assert deal_check.error == "metric_not_supported_for_model"
    assert 'Показатель "количество сделок"' in deal_check.message
    assert price_check.valid is False
    assert price_check.error == "metric_not_supported_for_model"
    assert 'Показатель "цена метра"' in price_check.message


def test_model_rejects_unknown_metric_request_instead_of_summary() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "period": {"label": "апрель"},
                "metrics": [],
            },
        ),
    )

    check = check_report_compatibility(frame, "модель космический показатель апрель")

    assert check.valid is False
    assert check.error == "unknown_metric_for_model"
    assert "Не нашел такой показатель в модели" in check.message


def test_model_blocks_sensitive_data_requests() -> None:
    frame = apply_report_semantics(
        build_query_frame(
            {
                "last_intent": "data_query",
                "report_type": "model",
                "period": {"label": "апрель"},
                "metrics": [],
            },
        ),
    )

    for text in (
        "модель покажи контакты",
        "модель телефоны участников",
        "модель паспортные данные",
        "модель договоры и номера документов",
    ):
        check = check_report_compatibility(frame, text)

        assert check.valid is False
        assert check.error == "sensitive_data_blocked_for_model"
        assert "по правилам безопасности" in check.message
        assert "телефоны" in check.message
        assert "номера документов" in check.message


def test_model_square_meters_uses_total_area_metric() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_kpi(session, date(2026, 4, 1), "Общая площадь", "model_total_area", Decimal("56279.3"), 1)
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "model",
            "period": {"label": "апрель"},
            "metrics": ["model_total_area"],
            "view": "model_kpi",
        },
    )

    assert query.metrics == ["model_total_area"]
    assert calculation.rows[0]["model_total_area"] == 56279.3
    assert "Общая площадь: 56 279.3 м2" in draft.text


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
    assert "Подключенные показатели модели:" in draft.text
    assert "- Выручка" in draft.text
    assert "- NPV" in draft.text


def test_model_raw_sheet_list_returns_public_sheet_names() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_raw_sheet(session, date(2026, 4, 1), "Финмодель", "financial_model", 100, 500)
    add_model_raw_sheet(session, date(2026, 4, 1), "Остатки", "remains", 20, 80)
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "model",
            "view": "model_raw_sheets",
            "dimension": "raw_sheet",
        },
    )

    assert query.table == "model_raw_sheets"
    assert calculation.row_count == 2
    assert "Листы модели:" in draft.text
    assert "- Финмодель" in draft.text
    assert "- Остатки" in draft.text


def test_model_raw_sheet_dimension_without_view_uses_raw_sheet_list() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_raw_sheet(session, date(2026, 4, 1), "Финмодель", "financial_model", 100, 500)
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "model",
            "dimension": "raw_sheet",
        },
    )

    assert query.table == "model_raw_sheets"
    assert calculation.row_count == 1
    assert "Листы модели:" in draft.text


def test_model_raw_rows_return_visible_cells_only() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_raw_sheet(session, date(2026, 4, 1), "Финмодель", "financial_model", 10, 20)
    add_model_raw_row(
        session,
        date(2026, 4, 1),
        "Финмодель",
        "financial_model",
        7,
        "Общая площадь",
        [
            (1, "A", "Общая площадь", None, False),
            (2, "B", None, Decimal("1234"), False),
            (3, "C", "+79999999999", None, True),
        ],
    )
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "model",
            "view": "model_raw_rows",
            "filters": {"raw_sheet": "финмодель"},
        },
    )

    assert query.table == "model_raw_rows"
    assert calculation.rows[0]["raw_sheet"] == "Финмодель"
    assert "Строка 7. Общая площадь" in draft.text
    assert "B: 1234" in draft.text
    assert "+79999999999" not in draft.text


def test_model_raw_search_filters_rows() -> None:
    session = create_session()
    add_model_source(session, date(2026, 4, 1))
    add_model_raw_sheet(session, date(2026, 4, 1), "Остатки", "remains", 10, 20)
    add_model_raw_row(
        session,
        date(2026, 4, 1),
        "Остатки",
        "remains",
        2,
        "Коммерческие помещения",
        [(1, "A", "Коммерческие помещения", None, False)],
    )
    add_model_raw_row(
        session,
        date(2026, 4, 1),
        "Остатки",
        "remains",
        3,
        "Машиноместа",
        [(1, "A", "Машиноместа", None, False)],
    )
    session.commit()

    draft, calculation, query = build_model_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "model",
            "view": "model_raw_search",
            "filters": {"raw_sheet": "остатки", "raw_query": "Коммерческие"},
        },
    )

    assert query.params["raw_sheet"] == "remains"
    assert calculation.row_count == 1
    assert "Коммерческие помещения" in draft.text
    assert "Машиноместа" not in draft.text
