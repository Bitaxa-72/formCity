from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0006"
down_revision: str | None = "20260625_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_for_sale_sources",
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
        op.create_index(f"ix_stock_for_sale_sources_{column}", "stock_for_sale_sources", [column])

    op.create_table(
        "stock_for_sale_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=True),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("row_label", sa.String(length=255), nullable=False),
        sa.Column("property_type", sa.String(length=64), nullable=False),
        sa.Column("floor_number", sa.Integer(), nullable=True),
        sa.Column("is_in_work", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ddu_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("dupt_markup_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("total_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("area_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit_count", sa.Integer(), nullable=True),
        sa.Column("ddu_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("dupt_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("total_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_month", "row_order"),
    )
    for column in ("project", "snapshot_month", "row_type", "row_label", "property_type", "floor_number", "is_in_work"):
        op.create_index(f"ix_stock_for_sale_facts_{column}", "stock_for_sale_facts", [column])


def downgrade() -> None:
    for column in reversed(("project", "snapshot_month", "row_type", "row_label", "property_type", "floor_number", "is_in_work")):
        op.drop_index(f"ix_stock_for_sale_facts_{column}", table_name="stock_for_sale_facts")
    op.drop_table("stock_for_sale_facts")

    for column in reversed(("project", "snapshot_month", "file_hash")):
        op.drop_index(f"ix_stock_for_sale_sources_{column}", table_name="stock_for_sale_sources")
    op.drop_table("stock_for_sale_sources")
