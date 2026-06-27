from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    telegram_chat_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    dialog_state: Mapped["DialogState"] = relationship(back_populates="user", cascade="all, delete-orphan")
    last_result: Mapped["LastResult | None"] = relationship(back_populates="user", cascade="all, delete-orphan")


class DialogState(Base):
    __tablename__ = "dialog_states"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="dialog_state")


class MessageHistory(Base):
    __tablename__ = "message_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    request_id: Mapped[str] = mapped_column(String(64), index=True)
    update_id: Mapped[int] = mapped_column(Integer)
    telegram_message_id: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(32))
    text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class LastResult(Base):
    __tablename__ = "last_results"
    __table_args__ = (UniqueConstraint("user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    query_frame: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="last_result")


class PaymentCalendarFact(Base):
    __tablename__ = "payment_calendar_facts"
    __table_args__ = (UniqueConstraint("project", "period_month", "article_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    article: Mapped[str] = mapped_column(String(255), index=True)
    article_kind: Mapped[str] = mapped_column(String(64), index=True)
    article_order: Mapped[int] = mapped_column(Integer)
    plan_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    fact_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    deviation_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RoadmapStep(Base):
    __tablename__ = "roadmap_steps"
    __table_args__ = (UniqueConstraint("project", "period_month", "row_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    row_order: Mapped[int] = mapped_column(Integer)
    step_no: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    parent_step_no: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    action_text: Mapped[str] = mapped_column(Text)
    min_work_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_work_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_total: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelSource(Base):
    __tablename__ = "model_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelMonthlyFact(Base):
    __tablename__ = "model_monthly_facts"
    __table_args__ = (
        UniqueConstraint("project", "snapshot_month", "scenario", "period_month", "source_sheet", "source_row", "source_col"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(32), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    period_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    row_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelKpiFact(Base):
    __tablename__ = "model_kpi_facts"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "scenario", "metric_name", "source_sheet", "source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    scenario: Mapped[str] = mapped_column(String(32), index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    normalized_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelComparisonFact(Base):
    __tablename__ = "model_comparison_facts"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "metric_name", "source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    current_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    plan_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    deviation_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    deviation_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelPassportFact(Base):
    __tablename__ = "model_passport_facts"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "metric_name", "source_sheet", "source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelAssumptionFact(Base):
    __tablename__ = "model_assumption_facts"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "metric_name", "source_sheet", "source_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    metric_key: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelRawSheet(Base):
    __tablename__ = "model_raw_sheets"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    max_row: Mapped[int] = mapped_column(Integer)
    max_column: Mapped[int] = mapped_column(Integer)
    row_count: Mapped[int] = mapped_column(Integer)
    cell_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelRawRow(Base):
    __tablename__ = "model_raw_rows"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name", "row_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    row_number: Mapped[int] = mapped_column(Integer, index=True)
    row_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    non_empty_cells: Mapped[int] = mapped_column(Integer)
    raw_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ModelRawCell(Base):
    __tablename__ = "model_raw_cells"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "source_file", "sheet_name", "row_number", "column_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    row_number: Mapped[int] = mapped_column(Integer, index=True)
    column_number: Mapped[int] = mapped_column(Integer, index=True)
    column_letter: Mapped[str] = mapped_column(String(16))
    value_type: Mapped[str] = mapped_column(String(32), index=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NonProjectExpenseSource(Base):
    __tablename__ = "non_project_expense_sources"
    __table_args__ = (UniqueConstraint("project", "period_month", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    filled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NonProjectExpenseFact(Base):
    __tablename__ = "non_project_expense_facts"
    __table_args__ = (UniqueConstraint("project", "period_month", "row_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    filled_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_order: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    item_kind: Mapped[str] = mapped_column(String(128), index=True)
    fm_category: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    item_name: Mapped[str] = mapped_column(Text)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    executed_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    remaining_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    reference_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    sensitive_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockForSaleSource(Base):
    __tablename__ = "stock_for_sale_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StockForSaleFact(Base):
    __tablename__ = "stock_for_sale_facts"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "row_order"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_order: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    row_label: Mapped[str] = mapped_column(String(255), index=True)
    property_type: Mapped[str] = mapped_column(String(64), index=True)
    floor_number: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    is_in_work: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    ddu_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    dupt_markup_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ddu_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    dupt_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SalesReportSource(Base):
    __tablename__ = "sales_report_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SalesReportFact(Base):
    __tablename__ = "sales_report_facts"
    __table_args__ = (
        UniqueConstraint("project", "snapshot_month", "segment", "metric_key", "owner_scope", "period_kind", "period_month", "source_col"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    segment: Mapped[str] = mapped_column(String(64), index=True)
    segment_label: Mapped[str] = mapped_column(String(255))
    metric_key: Mapped[str] = mapped_column(String(128), index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    owner_scope: Mapped[str] = mapped_column(String(64), index=True)
    period_kind: Mapped[str] = mapped_column(String(32), index=True)
    period_month: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    scenario: Mapped[str] = mapped_column(String(32), index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SalesPlanExecutionSource(Base):
    __tablename__ = "sales_plan_execution_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SalesPlanExecutionFact(Base):
    __tablename__ = "sales_plan_execution_facts"
    __table_args__ = (
        UniqueConstraint(
            "project",
            "snapshot_month",
            "block_kind",
            "segment",
            "metric_key",
            "owner_scope",
            "period_kind",
            "period_month",
            "year",
            "scenario",
            "source_row",
            "source_col",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    block_kind: Mapped[str] = mapped_column(String(64), index=True)
    block_label: Mapped[str] = mapped_column(String(255))
    segment: Mapped[str] = mapped_column(String(64), index=True)
    segment_label: Mapped[str] = mapped_column(String(255))
    metric_key: Mapped[str] = mapped_column(String(128), index=True)
    metric_name: Mapped[str] = mapped_column(String(255), index=True)
    owner_scope: Mapped[str] = mapped_column(String(64), index=True)
    period_kind: Mapped[str] = mapped_column(String(32), index=True)
    period_month: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    scenario: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentsReportSource(Base):
    __tablename__ = "agents_report_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "snapshot_date", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentsReportDeal(Base):
    __tablename__ = "agents_report_deals"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    row_order: Mapped[int] = mapped_column(Integer)
    agent_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    buyer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    ddu_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contract_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    commission_base_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    check_qw_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    check_gh_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    commission_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    commission_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    act_total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    remaining_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    act_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    budget_month: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    ddu_assignment_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    ddu_assignment_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    ddu_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    ddu_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    assignment_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    assignment_price_per_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    furniture_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sensitive_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AgentsReportMonthlyValue(Base):
    __tablename__ = "agents_report_monthly_values"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "deal_source_row", "value_kind", "period_kind", "period_month", "source_col", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    deal_source_row: Mapped[int] = mapped_column(Integer, index=True)
    value_kind: Mapped[str] = mapped_column(String(64), index=True)
    period_kind: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DebtBookingSource(Base):
    __tablename__ = "debt_booking_sources"
    __table_args__ = (UniqueConstraint("project", "snapshot_month", "snapshot_date", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DebtBookingItem(Base):
    __tablename__ = "debt_booking_items"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "source_sheet", "source_row", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    row_order: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    item_kind: Mapped[str] = mapped_column(String(128), index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    client_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_special_client: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    unit_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacts: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sensitive_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DebtBookingMonthlyValue(Base):
    __tablename__ = "debt_booking_monthly_values"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "item_source_row", "period_month", "source_col", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    item_source_row: Mapped[int] = mapped_column(Integer, index=True)
    item_kind: Mapped[str] = mapped_column(String(128), index=True)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    period_month: Mapped[date] = mapped_column(Date, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_col: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DebtBookingDeviation(Base):
    __tablename__ = "debt_booking_deviations"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    period_month: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    row_order: Mapped[int] = mapped_column(Integer)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    item_kind: Mapped[str] = mapped_column(String(128), index=True)
    section: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    client_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    plan_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    updated_plan_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    plan_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    fact_payment_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    remaining_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    fact_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sensitive_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DebtBookingRefusal(Base):
    __tablename__ = "debt_booking_refusals"
    __table_args__ = (UniqueConstraint("project", "snapshot_date", "source_row", "source_file"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    snapshot_month: Mapped[date] = mapped_column(Date, index=True)
    snapshot_date: Mapped[date] = mapped_column(Date, index=True)
    row_order: Mapped[int] = mapped_column(Integer)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    area_sqm: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    unit_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    full_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    payment_type: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    agency: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    manager_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sensitive_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(64))
    source_row: Mapped[int] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SummarySource(Base):
    __tablename__ = "summary_sources"
    __table_args__ = (UniqueConstraint("project", "file_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SummarySheet(Base):
    __tablename__ = "summary_sheets"
    __table_args__ = (UniqueConstraint("project", "source_file", "sheet_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    header_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_row: Mapped[int] = mapped_column(Integer)
    max_column: Mapped[int] = mapped_column(Integer)
    row_count: Mapped[int] = mapped_column(Integer)
    cell_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SummaryRow(Base):
    __tablename__ = "summary_rows"
    __table_args__ = (UniqueConstraint("project", "source_file", "sheet_name", "row_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    row_number: Mapped[int] = mapped_column(Integer, index=True)
    row_type: Mapped[str] = mapped_column(String(64), index=True)
    row_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_label: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    unit_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    non_empty_cells: Mapped[int] = mapped_column(Integer)
    raw_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sensitive_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SummaryCell(Base):
    __tablename__ = "summary_cells"
    __table_args__ = (UniqueConstraint("project", "source_file", "sheet_name", "row_number", "column_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project: Mapped[str] = mapped_column(String(64), index=True)
    source_file: Mapped[str] = mapped_column(String(255), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255), index=True)
    sheet_kind: Mapped[str] = mapped_column(String(128), index=True)
    row_number: Mapped[int] = mapped_column(Integer, index=True)
    column_number: Mapped[int] = mapped_column(Integer, index=True)
    column_letter: Mapped[str] = mapped_column(String(16))
    header_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    header_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    header_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    value_type: Mapped[str] = mapped_column(String(32), index=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    value_bool: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
