from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0007"
down_revision: str | None = "20260625_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_report_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "file_hash"),
    )
    for column in ("project", "snapshot_month", "file_hash"):
        op.create_index(f"ix_sales_report_sources_{column}", "sales_report_sources", [column])

    op.create_table(
        "sales_report_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("segment", sa.String(length=64), nullable=False),
        sa.Column("segment_label", sa.String(length=255), nullable=False),
        sa.Column("metric_key", sa.String(length=128), nullable=False),
        sa.Column("metric_name", sa.String(length=255), nullable=False),
        sa.Column("owner_scope", sa.String(length=64), nullable=False),
        sa.Column("period_kind", sa.String(length=32), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=True),
        sa.Column("scenario", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "project",
            "snapshot_month",
            "segment",
            "metric_key",
            "owner_scope",
            "period_kind",
            "period_month",
            "source_col",
        ),
    )
    for column in ("project", "snapshot_month", "segment", "metric_key", "metric_name", "owner_scope", "period_kind", "period_month", "scenario"):
        op.create_index(f"ix_sales_report_facts_{column}", "sales_report_facts", [column])


def downgrade() -> None:
    for column in reversed(("project", "snapshot_month", "segment", "metric_key", "metric_name", "owner_scope", "period_kind", "period_month", "scenario")):
        op.drop_index(f"ix_sales_report_facts_{column}", table_name="sales_report_facts")
    op.drop_table("sales_report_facts")

    for column in reversed(("project", "snapshot_month", "file_hash")):
        op.drop_index(f"ix_sales_report_sources_{column}", table_name="sales_report_sources")
    op.drop_table("sales_report_sources")
