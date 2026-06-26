from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


NON_PROJECT_EXPENSES_GROUP_BY_COLUMNS = {
    "period": "period_month",
    "month": "period_month",
    "item_kind": "item_kind",
    "fm_category": "fm_category",
    "item_name": "item_name",
    "row_type": "row_type",
}

NON_PROJECT_EXPENSES_FILTER_COLUMNS = {
    "item_kind": "item_kind",
    "fm_category": "fm_category",
    "item_name": "item_name",
    "item_name_contains": "item_name",
    "row_type": "row_type",
}

NON_PROJECT_EXPENSES_DIMENSION_COLUMNS = {
    "period_month": "period_month",
    "period": "period_month",
    "month": "period_month",
    "item_kind": "item_kind",
    "fm_category": "fm_category",
    "item_name": "item_name",
    "row_type": "row_type",
}


NON_PROJECT_EXPENSES_SQL_TEMPLATE = ReportSQLTemplate(
    table="non_project_expense_facts",
    date_column="period_month",
    project_column="project",
    metrics={
        "amount": MetricSQLSpec("SUM(amount)", "amount"),
        "executed_amount": MetricSQLSpec("SUM(executed_amount)", "executed_amount"),
        "remaining_amount": MetricSQLSpec("SUM(remaining_amount)", "remaining_amount"),
    },
    group_by_columns=NON_PROJECT_EXPENSES_GROUP_BY_COLUMNS,
    filter_columns=NON_PROJECT_EXPENSES_FILTER_COLUMNS,
    dimension_columns=NON_PROJECT_EXPENSES_DIMENSION_COLUMNS,
)
