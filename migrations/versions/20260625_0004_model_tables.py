from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0004"
down_revision: str | None = "20260625_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "file_hash"),
    )
    op.create_index("ix_model_sources_project", "model_sources", ["project"])
    op.create_index("ix_model_sources_snapshot_month", "model_sources", ["snapshot_month"])
    op.create_index("ix_model_sources_file_hash", "model_sources", ["file_hash"])

    op.create_table(
        "model_monthly_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=32), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("period_status", sa.String(length=64), nullable=True),
        sa.Column("row_code", sa.String(length=64), nullable=True),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=True),
        sa.Column("value", sa.Numeric(20, 4), nullable=True),
        sa.Column("normalized_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "scenario", "period_month", "source_sheet", "source_row", "source_col"),
    )
    for column in ("project", "snapshot_month", "scenario", "period_month", "period_status", "row_code", "section", "metric_name", "metric_key", "is_sensitive"):
        op.create_index(f"ix_model_monthly_facts_{column}", "model_monthly_facts", [column])

    op.create_table(
        "model_kpi_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("scenario", sa.String(length=32), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=True),
        sa.Column("value", sa.Numeric(20, 4), nullable=True),
        sa.Column("normalized_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "scenario", "metric_name", "source_sheet", "source_row"),
    )
    for column in ("project", "snapshot_month", "scenario", "section", "metric_name", "metric_key", "is_sensitive"):
        op.create_index(f"ix_model_kpi_facts_{column}", "model_kpi_facts", [column])

    op.create_table(
        "model_comparison_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=True),
        sa.Column("current_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("plan_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("deviation_value", sa.Numeric(20, 4), nullable=True),
        sa.Column("deviation_percent", sa.Numeric(12, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "metric_name", "source_row"),
    )
    for column in ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive"):
        op.create_index(f"ix_model_comparison_facts_{column}", "model_comparison_facts", [column])

    op.create_table(
        "model_passport_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=True),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "metric_name", "source_sheet", "source_row"),
    )
    for column in ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive"):
        op.create_index(f"ix_model_passport_facts_{column}", "model_passport_facts", [column])

    op.create_table(
        "model_assumption_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=True),
        sa.Column("value", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "metric_name", "source_sheet", "source_row"),
    )
    for column in ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive"):
        op.create_index(f"ix_model_assumption_facts_{column}", "model_assumption_facts", [column])


def downgrade() -> None:
    for table, columns in (
        ("model_assumption_facts", ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive")),
        ("model_passport_facts", ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive")),
        ("model_comparison_facts", ("project", "snapshot_month", "section", "metric_name", "metric_key", "is_sensitive")),
        ("model_kpi_facts", ("project", "snapshot_month", "scenario", "section", "metric_name", "metric_key", "is_sensitive")),
        ("model_monthly_facts", ("project", "snapshot_month", "scenario", "period_month", "period_status", "row_code", "section", "metric_name", "metric_key", "is_sensitive")),
    ):
        for column in reversed(columns):
            op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.drop_table(table)

    op.drop_index("ix_model_sources_file_hash", table_name="model_sources")
    op.drop_index("ix_model_sources_snapshot_month", table_name="model_sources")
    op.drop_index("ix_model_sources_project", table_name="model_sources")
    op.drop_table("model_sources")
