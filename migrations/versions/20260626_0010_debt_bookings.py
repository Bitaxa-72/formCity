from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260626_0010"
down_revision: str | None = "20260626_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "debt_booking_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "snapshot_date", "file_hash"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "file_hash"):
        op.create_index(f"ix_debt_booking_sources_{column}", "debt_booking_sources", [column])

    op.create_table(
        "debt_booking_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("item_kind", sa.String(length=128), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("manager_name", sa.Text(), nullable=True),
        sa.Column("is_special_client", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unit_number", sa.String(length=255), nullable=True),
        sa.Column("total_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("contacts", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sensitive_fields", sa.JSON(), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "source_sheet", "source_row", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "row_type", "item_kind", "section", "is_special_client", "unit_number", "is_sensitive"):
        op.create_index(f"ix_debt_booking_items_{column}", "debt_booking_items", [column])

    op.create_table(
        "debt_booking_monthly_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("item_source_row", sa.Integer(), nullable=False),
        sa.Column("item_kind", sa.String(length=128), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 2), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "item_source_row", "period_month", "source_col", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "item_source_row", "item_kind", "row_type", "period_month"):
        op.create_index(f"ix_debt_booking_monthly_values_{column}", "debt_booking_monthly_values", [column])

    op.create_table(
        "debt_booking_deviations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=True),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("item_kind", sa.String(length=128), nullable=False),
        sa.Column("section", sa.String(length=255), nullable=True),
        sa.Column("client_name", sa.Text(), nullable=True),
        sa.Column("unit_number", sa.String(length=255), nullable=True),
        sa.Column("plan_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("updated_plan_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("plan_comment", sa.Text(), nullable=True),
        sa.Column("fact_payment_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("remaining_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("fact_comment", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sensitive_fields", sa.JSON(), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "period_month", "row_type", "item_kind", "section", "unit_number", "is_sensitive"):
        op.create_index(f"ix_debt_booking_deviations_{column}", "debt_booking_deviations", [column])

    op.create_table(
        "debt_booking_refusals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=255), nullable=True),
        sa.Column("area_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit_number", sa.String(length=255), nullable=True),
        sa.Column("full_price_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("payment_type", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("agency", sa.String(length=255), nullable=True),
        sa.Column("manager_name", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sensitive_fields", sa.JSON(), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "status", "unit_number", "payment_type", "agency", "is_sensitive"):
        op.create_index(f"ix_debt_booking_refusals_{column}", "debt_booking_refusals", [column])


def downgrade() -> None:
    for column in reversed(("project", "snapshot_month", "snapshot_date", "status", "unit_number", "payment_type", "agency", "is_sensitive")):
        op.drop_index(f"ix_debt_booking_refusals_{column}", table_name="debt_booking_refusals")
    op.drop_table("debt_booking_refusals")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "period_month", "row_type", "item_kind", "section", "unit_number", "is_sensitive")):
        op.drop_index(f"ix_debt_booking_deviations_{column}", table_name="debt_booking_deviations")
    op.drop_table("debt_booking_deviations")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "item_source_row", "item_kind", "row_type", "period_month")):
        op.drop_index(f"ix_debt_booking_monthly_values_{column}", table_name="debt_booking_monthly_values")
    op.drop_table("debt_booking_monthly_values")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "row_type", "item_kind", "section", "is_special_client", "unit_number", "is_sensitive")):
        op.drop_index(f"ix_debt_booking_items_{column}", table_name="debt_booking_items")
    op.drop_table("debt_booking_items")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "file_hash")):
        op.drop_index(f"ix_debt_booking_sources_{column}", table_name="debt_booking_sources")
    op.drop_table("debt_booking_sources")
