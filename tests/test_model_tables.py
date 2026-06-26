from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.db.models import Base, ModelKpiFact, ModelMonthlyFact, ModelSource


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
        session.add_all([source, monthly, kpi])
        session.commit()

    with Session(engine) as session:
        assert session.query(ModelMonthlyFact).one().is_sensitive is True
        assert session.query(ModelKpiFact).one().metric_name == "revenue"
