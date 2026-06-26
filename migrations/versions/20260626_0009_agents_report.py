from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260626_0009"
down_revision: str | None = "20260625_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents_report_sources",
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
        op.create_index(f"ix_agents_report_sources_{column}", "agents_report_sources", [column])

    op.create_table(
        "agents_report_deals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("unit_number", sa.String(length=64), nullable=True),
        sa.Column("buyer_name", sa.Text(), nullable=True),
        sa.Column("ddu_number", sa.String(length=255), nullable=True),
        sa.Column("contract_date", sa.Date(), nullable=True),
        sa.Column("area_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("commission_base_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("check_qw_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("check_gh_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(12, 6), nullable=True),
        sa.Column("commission_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("act_total_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("remaining_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("act_info", sa.Text(), nullable=True),
        sa.Column("budget_month", sa.Date(), nullable=True),
        sa.Column("ddu_assignment_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("ddu_assignment_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("ddu_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("ddu_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("assignment_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("assignment_price_per_sqm", sa.Numeric(20, 4), nullable=True),
        sa.Column("furniture_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sensitive_fields", sa.JSON(), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "unit_number", "contract_date", "budget_month", "is_sensitive"):
        op.create_index(f"ix_agents_report_deals_{column}", "agents_report_deals", [column])

    op.create_table(
        "agents_report_monthly_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("snapshot_month", sa.Date(), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("deal_source_row", sa.Integer(), nullable=False),
        sa.Column("value_kind", sa.String(length=64), nullable=False),
        sa.Column("period_kind", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=True),
        sa.Column("value", sa.Numeric(20, 2), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_col", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "snapshot_date", "deal_source_row", "value_kind", "period_kind", "period_month", "source_col", "source_file"),
    )
    for column in ("project", "snapshot_month", "snapshot_date", "deal_source_row", "value_kind", "period_kind", "period_month"):
        op.create_index(f"ix_agents_report_monthly_values_{column}", "agents_report_monthly_values", [column])


def downgrade() -> None:
    for column in reversed(("project", "snapshot_month", "snapshot_date", "deal_source_row", "value_kind", "period_kind", "period_month")):
        op.drop_index(f"ix_agents_report_monthly_values_{column}", table_name="agents_report_monthly_values")
    op.drop_table("agents_report_monthly_values")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "unit_number", "contract_date", "budget_month", "is_sensitive")):
        op.drop_index(f"ix_agents_report_deals_{column}", table_name="agents_report_deals")
    op.drop_table("agents_report_deals")

    for column in reversed(("project", "snapshot_month", "snapshot_date", "file_hash")):
        op.drop_index(f"ix_agents_report_sources_{column}", table_name="agents_report_sources")
    op.drop_table("agents_report_sources")
