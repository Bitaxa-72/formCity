from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260626_0011"
down_revision: str | None = "20260626_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "summary_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "file_hash"),
    )
    for column in ("project", "file_hash"):
        op.create_index(f"ix_summary_sources_{column}", "summary_sources", [column])

    op.create_table(
        "summary_sheets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=True),
        sa.Column("max_row", sa.Integer(), nullable=False),
        sa.Column("max_column", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("cell_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "source_file", "sheet_name"),
    )
    for column in ("project", "source_file", "sheet_name", "sheet_kind"):
        op.create_index(f"ix_summary_sheets_{column}", "summary_sheets", [column])

    op.create_table(
        "summary_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("row_label", sa.Text(), nullable=True),
        sa.Column("period_label", sa.String(length=255), nullable=True),
        sa.Column("unit_number", sa.String(length=255), nullable=True),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("non_empty_cells", sa.Integer(), nullable=False),
        sa.Column("raw_values", sa.JSON(), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sensitive_fields", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "source_file", "sheet_name", "row_number"),
    )
    for column in ("project", "source_file", "sheet_name", "sheet_kind", "row_number", "row_type", "period_label", "unit_number", "is_sensitive"):
        op.create_index(f"ix_summary_rows_{column}", "summary_rows", [column])

    op.create_table(
        "summary_cells",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_number", sa.Integer(), nullable=False),
        sa.Column("column_letter", sa.String(length=16), nullable=False),
        sa.Column("header_row", sa.Integer(), nullable=True),
        sa.Column("header_label", sa.Text(), nullable=True),
        sa.Column("header_key", sa.String(length=255), nullable=True),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(24, 6), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "source_file", "sheet_name", "row_number", "column_number"),
    )
    for column in (
        "project",
        "source_file",
        "sheet_name",
        "sheet_kind",
        "row_number",
        "column_number",
        "header_key",
        "value_type",
        "value_date",
        "is_sensitive",
    ):
        op.create_index(f"ix_summary_cells_{column}", "summary_cells", [column])


def downgrade() -> None:
    for column in reversed((
        "project",
        "source_file",
        "sheet_name",
        "sheet_kind",
        "row_number",
        "column_number",
        "header_key",
        "value_type",
        "value_date",
        "is_sensitive",
    )):
        op.drop_index(f"ix_summary_cells_{column}", table_name="summary_cells")
    op.drop_table("summary_cells")

    for column in reversed(("project", "source_file", "sheet_name", "sheet_kind", "row_number", "row_type", "period_label", "unit_number", "is_sensitive")):
        op.drop_index(f"ix_summary_rows_{column}", table_name="summary_rows")
    op.drop_table("summary_rows")

    for column in reversed(("project", "source_file", "sheet_name", "sheet_kind")):
        op.drop_index(f"ix_summary_sheets_{column}", table_name="summary_sheets")
    op.drop_table("summary_sheets")

    for column in reversed(("project", "file_hash")):
        op.drop_index(f"ix_summary_sources_{column}", table_name="summary_sources")
    op.drop_table("summary_sources")
