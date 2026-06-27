from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, SummaryCell, SummaryRow, SummarySheet, SummarySource
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
from app.reports.summary.corrections import build_summary_correction


def create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def add_summary_data(session: Session) -> None:
    session.add_all(
        [
            SummarySource(project="obvodny", file_name="Сводная_Обводный.xlsx", file_hash="hash1"),
            SummarySource(project="moskovsky", file_name="Сводная_Московский.xlsx", file_hash="hash2"),
        ],
    )
    session.add_all(
        [
            SummarySheet(
                project="obvodny",
                source_file="Сводная_Обводный.xlsx",
                sheet_name="Апартаменты",
                sheet_kind="residential_units",
                header_row=1,
                max_row=3,
                max_column=4,
                row_count=3,
                cell_count=8,
            ),
            SummarySheet(
                project="moskovsky",
                source_file="Сводная_Московский.xlsx",
                sheet_name="Коммерция",
                sheet_kind="commercial_units",
                header_row=1,
                max_row=2,
                max_column=4,
                row_count=2,
                cell_count=4,
            ),
        ],
    )
    session.add_all(
        [
            SummaryRow(
                project="obvodny",
                source_file="Сводная_Обводный.xlsx",
                sheet_name="Апартаменты",
                sheet_kind="residential_units",
                row_number=1,
                row_type="header",
                row_label="ФИО клиента",
                period_label=None,
                unit_number=None,
                customer_name=None,
                non_empty_cells=4,
                raw_values={"A": "ФИО клиента"},
                is_sensitive=True,
                sensitive_fields={"customer_name": True},
            ),
            SummaryRow(
                project="obvodny",
                source_file="Сводная_Обводный.xlsx",
                sheet_name="Апартаменты",
                sheet_kind="residential_units",
                row_number=2,
                row_type="detail",
                row_label="Иванов Иван",
                period_label=None,
                unit_number="1.1",
                customer_name="Иванов Иван",
                non_empty_cells=4,
                raw_values={"ФИО клиента": "Иванов Иван", "Оплачено": 1000, "Остаток": 200},
                is_sensitive=True,
                sensitive_fields={"customer_name": True, "unit_number": True},
            ),
            SummaryRow(
                project="obvodny",
                source_file="Сводная_Обводный.xlsx",
                sheet_name="Апартаменты",
                sheet_kind="residential_units",
                row_number=3,
                row_type="detail",
                row_label="Петров Петр",
                period_label=None,
                unit_number="1.2",
                customer_name="Петров Петр",
                non_empty_cells=4,
                raw_values={"ФИО клиента": "Петров Петр", "Оплачено": 3000, "Остаток": 400},
                is_sensitive=True,
                sensitive_fields={"customer_name": True, "unit_number": True},
            ),
            SummaryRow(
                project="moskovsky",
                source_file="Сводная_Московский.xlsx",
                sheet_name="Коммерция",
                sheet_kind="commercial_units",
                row_number=2,
                row_type="detail",
                row_label="Коммерция",
                period_label=None,
                unit_number=None,
                customer_name=None,
                non_empty_cells=4,
                raw_values={"Оплачено": 5000},
                is_sensitive=False,
                sensitive_fields={},
            ),
        ],
    )
    session.add_all(
        [
            summary_cell("obvodny", "Апартаменты", "residential_units", 2, 1, "ФИО клиента", "фио_клиента", value_text="Иванов Иван", sensitive=True),
            summary_cell("obvodny", "Апартаменты", "residential_units", 2, 2, "Оплачено", "оплачено", value_number=Decimal("1000")),
            summary_cell("obvodny", "Апартаменты", "residential_units", 2, 3, "Остаток", "остаток", value_number=Decimal("200")),
            summary_cell("obvodny", "Апартаменты", "residential_units", 3, 1, "ФИО клиента", "фио_клиента", value_text="Петров Петр", sensitive=True),
            summary_cell("obvodny", "Апартаменты", "residential_units", 3, 2, "Оплачено", "оплачено", value_number=Decimal("3000")),
            summary_cell("obvodny", "Апартаменты", "residential_units", 3, 3, "Остаток", "остаток", value_number=Decimal("400")),
            summary_cell("moskovsky", "Коммерция", "commercial_units", 2, 1, "Оплачено", "оплачено", value_number=Decimal("5000"), source_file="Сводная_Московский.xlsx"),
            summary_cell("moskovsky", "Коммерция", "commercial_units", 2, 2, "Площадь", "площадь", value_number=Decimal("42"), source_file="Сводная_Московский.xlsx"),
        ],
    )
    session.commit()


def summary_cell(
    project: str,
    sheet_name: str,
    sheet_kind: str,
    row_number: int,
    column_number: int,
    header_label: str,
    header_key: str,
    value_text: str | None = None,
    value_number: Decimal | None = None,
    sensitive: bool = False,
    source_file: str = "Сводная_Обводный.xlsx",
) -> SummaryCell:
    return SummaryCell(
        project=project,
        source_file=source_file,
        sheet_name=sheet_name,
        sheet_kind=sheet_kind,
        row_number=row_number,
        column_number=column_number,
        column_letter=chr(64 + column_number),
        header_row=1,
        header_label=header_label,
        header_key=header_key,
        value_type="number" if value_number is not None else "text",
        value_text=value_text,
        value_number=value_number,
        value_date=None,
        value_bool=None,
        is_sensitive=sensitive,
    )


def build_summary_answer(session: Session, state: dict[str, object], text: str | None = None):
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


def test_summary_overview_returns_safe_counts_by_project() -> None:
    session = create_session()
    add_summary_data(session)

    draft, calculation, _query = build_summary_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "summary",
            "view": "summary_overview",
        },
    )

    assert calculation.row_count == 2
    assert "Сводный отчет" in draft.text
    assert "Проект: Обводный" in draft.text
    assert "Проект: Московский" in draft.text
    assert "Количество листов: 1" in draft.text
    assert "Иванов" not in draft.text
    assert "Петров" not in draft.text


def test_summary_values_sums_safe_header() -> None:
    session = create_session()
    add_summary_data(session)

    draft, calculation, _query = build_summary_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "summary",
            "project": "obvodny",
            "view": "summary_values",
            "metrics": ["summary_value_sum"],
            "filters": {"header_key": "оплачено"},
        },
    )

    assert calculation.row_count == 1
    assert "Проект: Обводный" in draft.text
    assert "Сумма значений: 4 000" in draft.text


def test_summary_available_headers_excludes_sensitive_values() -> None:
    session = create_session()
    add_summary_data(session)

    draft, calculation, _query = build_summary_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "summary",
            "view": "summary_available_headers",
            "dimension": "header_key",
        },
    )

    assert calculation.row_count == 3
    assert "Колонки:" in draft.text
    assert "- оплачено" in draft.text
    assert "- остаток" in draft.text
    assert "- площадь" in draft.text
    assert "фио_клиента" not in draft.text


def test_summary_available_sheet_kinds_formats_labels() -> None:
    session = create_session()
    add_summary_data(session)

    draft, calculation, _query = build_summary_answer(
        session,
        {
            "last_intent": "dimension_query",
            "report_type": "summary",
            "view": "summary_available_sheet_kinds",
            "dimension": "sheet_kind",
        },
    )

    assert calculation.row_count == 2
    assert "- Жилые помещения" in draft.text
    assert "- Коммерческие помещения" in draft.text


def test_summary_sensitive_request_is_blocked() -> None:
    session = create_session()
    add_summary_data(session)

    compatibility, calculation, query = build_summary_answer(
        session,
        {
            "last_intent": "data_query",
            "report_type": "summary",
            "view": "summary_overview",
        },
        text="сводный отчет покажи ФИО клиентов и номера ДДУ",
    )

    assert compatibility.valid is False
    assert calculation is None
    assert query is None
    assert "не вывожу" in compatibility.message
    assert "ФИО" in compatibility.message


def test_summary_correction_recognizes_paid_values() -> None:
    parsed = build_summary_correction("сводный отчет обводный сумма оплачено")

    assert parsed is not None
    assert parsed.state_delta.report_type == "summary"
    assert parsed.state_delta.project == "obvodny"
    assert parsed.state_delta.view == "summary_values"
    assert parsed.state_delta.metrics == ["summary_value_sum"]
    assert parsed.state_delta.filters == {"header_key": "оплачено"}
