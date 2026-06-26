from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260625_0003"
down_revision: str | None = "20260622_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roadmap_steps",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project", sa.String(length=64), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("row_order", sa.Integer(), nullable=False),
        sa.Column("step_no", sa.Integer(), nullable=True),
        sa.Column("parent_step_no", sa.Integer(), nullable=True),
        sa.Column("action_text", sa.Text(), nullable=False),
        sa.Column("min_work_days", sa.Integer(), nullable=True),
        sa.Column("max_work_days", sa.Integer(), nullable=True),
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_total", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("project", "period_month", "row_order"),
    )
    op.create_index("ix_roadmap_steps_project", "roadmap_steps", ["project"])
    op.create_index("ix_roadmap_steps_period_month", "roadmap_steps", ["period_month"])
    op.create_index("ix_roadmap_steps_step_no", "roadmap_steps", ["step_no"])
    op.create_index("ix_roadmap_steps_parent_step_no", "roadmap_steps", ["parent_step_no"])
    op.create_index("ix_roadmap_steps_is_external", "roadmap_steps", ["is_external"])
    op.create_index("ix_roadmap_steps_is_total", "roadmap_steps", ["is_total"])


def downgrade() -> None:
    op.drop_index("ix_roadmap_steps_is_total", table_name="roadmap_steps")
    op.drop_index("ix_roadmap_steps_is_external", table_name="roadmap_steps")
    op.drop_index("ix_roadmap_steps_parent_step_no", table_name="roadmap_steps")
    op.drop_index("ix_roadmap_steps_step_no", table_name="roadmap_steps")
    op.drop_index("ix_roadmap_steps_period_month", table_name="roadmap_steps")
    op.drop_index("ix_roadmap_steps_project", table_name="roadmap_steps")
    op.drop_table("roadmap_steps")
