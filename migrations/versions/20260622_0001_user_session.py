from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260622_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=255), nullable=False),
        sa.Column("telegram_chat_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "dialog_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_dialog_states_user_id", "dialog_states", ["user_id"])

    op.create_table(
        "message_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("update_id", sa.Integer(), nullable=False),
        sa.Column("telegram_message_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_message_history_user_id", "message_history", ["user_id"])
    op.create_index("ix_message_history_request_id", "message_history", ["request_id"])
    op.create_index("ix_message_history_created_at", "message_history", ["created_at"])

    op.create_table(
        "last_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("query_frame", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_last_results_user_id", "last_results", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_last_results_user_id", table_name="last_results")
    op.drop_table("last_results")
    op.drop_index("ix_message_history_created_at", table_name="message_history")
    op.drop_index("ix_message_history_request_id", table_name="message_history")
    op.drop_index("ix_message_history_user_id", table_name="message_history")
    op.drop_table("message_history")
    op.drop_index("ix_dialog_states_user_id", table_name="dialog_states")
    op.drop_table("dialog_states")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
