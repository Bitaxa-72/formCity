from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260622_0002"
down_revision: str | None = "20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_calendar_facts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("article", sa.String(length=255), nullable=False),
        sa.Column("article_kind", sa.String(length=64), nullable=False),
        sa.Column("article_order", sa.Integer(), nullable=False),
        sa.Column("plan_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("fact_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("deviation_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "period_month", "article_order"),
    )
    op.create_index("ix_payment_calendar_facts_project", "payment_calendar_facts", ["project"])
    op.create_index("ix_payment_calendar_facts_period_month", "payment_calendar_facts", ["period_month"])
    op.create_index("ix_payment_calendar_facts_article", "payment_calendar_facts", ["article"])
    op.create_index("ix_payment_calendar_facts_article_kind", "payment_calendar_facts", ["article_kind"])


def downgrade() -> None:
    op.drop_index("ix_payment_calendar_facts_article_kind", table_name="payment_calendar_facts")
    op.drop_index("ix_payment_calendar_facts_article", table_name="payment_calendar_facts")
    op.drop_index("ix_payment_calendar_facts_period_month", table_name="payment_calendar_facts")
    op.drop_index("ix_payment_calendar_facts_project", table_name="payment_calendar_facts")
    op.drop_table("payment_calendar_facts")
