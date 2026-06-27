from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db.models import Base, ModelKpiFact, ModelMonthlyFact, ModelRawCell, ModelSource


def test_model_tables_are_registered_in_metadata() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    tables = set(inspect(engine).get_table_names())

    assert "model_sources" in tables
    assert "model_monthly_facts" in tables
    assert "model_kpi_facts" in tables
    assert "model_comparison_facts" in tables
    assert "model_passport_facts" in tables
    assert "model_assumption_facts" in tables
    assert "model_raw_sheets" in tables
    assert "model_raw_rows" in tables
    assert "model_raw_cells" in tables


def test_model_tables_can_store_sensitive_rows() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = ModelSource(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            file_name="model.xlsx",
            file_hash="hash",
        )
        monthly = ModelMonthlyFact(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            scenario="current",
            period_month=date(2026, 5, 1),
            metric_name="document number",
            value=None,
            unit=None,
            is_sensitive=True,
            sensitive_kind="document_number",
            source_sheet="passport",
            source_row=1,
            source_col=2,
        )
        kpi = ModelKpiFact(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            scenario="current",
            metric_name="revenue",
            value=10,
            source_sheet="kpi",
            source_row=1,
        )
        raw_cell = ModelRawCell(
            project="obvodny",
            snapshot_month=date(2026, 4, 1),
            source_file="model.xlsx",
            sheet_name="Финмодель",
            sheet_kind="financial_model",
            row_number=1,
            column_number=1,
            column_letter="A",
            value_type="text",
            value_text="doc 12345",
            is_sensitive=True,
            sensitive_kind="document_number",
        )
        session.add_all([source, monthly, kpi, raw_cell])
        session.commit()

    with Session(engine) as session:
        assert session.query(ModelMonthlyFact).one().is_sensitive is True
        assert session.query(ModelKpiFact).one().metric_name == "revenue"
        assert session.query(ModelRawCell).one().sensitive_kind == "document_number"
