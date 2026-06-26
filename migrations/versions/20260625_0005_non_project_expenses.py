from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0005"
down_revision: str | None = "20260625_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "non_project_expense_sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("filled_at", sa.Date(), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("imported_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "period_month", "file_hash"),
    )
    op.create_index("ix_non_project_expense_sources_project", "non_project_expense_sources", ["project"])
    op.create_index("ix_non_project_expense_sources_period_month", "non_project_expense_sources", ["period_month"])
    op.create_index("ix_non_project_expense_sources_file_hash", "non_project_expense_sources", ["file_hash"])

    op.create_table(
        "non_project_expense_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("filled_at", sa.Date(), nullable=True),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(length=64), nullable=False),
        sa.Column("item_kind", sa.String(length=128), nullable=False),
        sa.Column("fm_category", sa.String(length=255), nullable=True),
        sa.Column("item_name", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("executed_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("remaining_amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("reference_text", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sensitive_kind", sa.String(length=64), nullable=True),
        sa.Column("source_sheet", sa.String(length=64), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "period_month", "row_order"),
    )
    for column in ("project", "period_month", "row_type", "item_kind", "fm_category", "is_sensitive"):
        op.create_index(f"ix_non_project_expense_facts_{column}", "non_project_expense_facts", [column])


def downgrade() -> None:
    for column in reversed(("project", "period_month", "row_type", "item_kind", "fm_category", "is_sensitive")):
        op.drop_index(f"ix_non_project_expense_facts_{column}", table_name="non_project_expense_facts")
    op.drop_table("non_project_expense_facts")

    op.drop_index("ix_non_project_expense_sources_file_hash", table_name="non_project_expense_sources")
    op.drop_index("ix_non_project_expense_sources_period_month", table_name="non_project_expense_sources")
    op.drop_index("ix_non_project_expense_sources_project", table_name="non_project_expense_sources")
    op.drop_table("non_project_expense_sources")
