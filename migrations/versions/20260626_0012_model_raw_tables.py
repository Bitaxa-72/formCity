from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260626_0012"
down_revision: str | None = "20260626_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_raw_sheets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("max_row", sa.Integer(), nullable=False),
        sa.Column("max_column", sa.Integer(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("cell_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name"),
    )
    for column in ("project", "snapshot_month", "source_file", "sheet_name", "sheet_kind"):
        op.create_index(f"ix_model_raw_sheets_{column}", "model_raw_sheets", [column])

    op.create_table(
        "model_raw_rows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("row_label", sa.Text(), nullable=True),
        sa.Column("non_empty_cells", sa.Integer(), nullable=False),
        sa.Column("raw_values", sa.JSON(), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name", "row_number"),
    )
    for column in ("project", "snapshot_month", "source_file", "sheet_name", "sheet_kind", "row_number", "is_sensitive"):
        op.create_index(f"ix_model_raw_rows_{column}", "model_raw_rows", [column])

    op.create_table(
        "model_raw_cells",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=False),
        sa.Column("sheet_name", sa.String(length=255), nullable=False),
        sa.Column("sheet_kind", sa.String(length=128), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("column_number", sa.Integer(), nullable=False),
        sa.Column("column_letter", sa.String(length=16), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=True),
        sa.Column("value_number", sa.Numeric(24, 6), nullable=True),
        sa.Column("value_date", sa.Date(), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name", "row_number", "column_number"),
    )
    for column in (
        "project",
        "snapshot_month",
        "source_file",
        "sheet_name",
        "sheet_kind",
        "row_number",
        "column_number",
        "value_type",
        "value_date",
        "is_sensitive",
    ):
        op.create_index(f"ix_model_raw_cells_{column}", "model_raw_cells", [column])


def downgrade() -> None:
    for column in reversed(
        (
            "project",
            "snapshot_month",
            "source_file",
            "sheet_name",
            "sheet_kind",
            "row_number",
            "column_number",
            "value_type",
            "value_date",
            "is_sensitive",
        ),
    ):
        op.drop_index(f"ix_model_raw_cells_{column}", table_name="model_raw_cells")
    op.drop_table("model_raw_cells")

    for column in reversed(("project", "snapshot_month", "source_file", "sheet_name", "sheet_kind", "row_number", "is_sensitive")):
        op.drop_index(f"ix_model_raw_rows_{column}", table_name="model_raw_rows")
    op.drop_table("model_raw_rows")

    for column in reversed(("project", "snapshot_month", "source_file", "sheet_name", "sheet_kind")):
        op.drop_index(f"ix_model_raw_sheets_{column}", table_name="model_raw_sheets")
    op.drop_table("model_raw_sheets")
