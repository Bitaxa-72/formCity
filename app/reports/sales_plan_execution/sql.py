from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


SALES_PLAN_EXECUTION_GROUP_BY_COLUMNS = {
    "month": "period_month",
    "period": "period_month",
    "snapshot_month": "snapshot_month",
    "block_kind": "block_kind",
    "segment": "segment",
    "metric_key": "metric_key",
    "owner_scope": "owner_scope",
    "period_kind": "period_kind",
    "period_month": "period_month",
    "year": "year",
    "scenario": "scenario",
}

SALES_PLAN_EXECUTION_FILTER_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "snapshot_date": "snapshot_date",
    "block_kind": "block_kind",
    "segment": "segment",
    "metric_key": "metric_key",
    "owner_scope": "owner_scope",
    "period_kind": "period_kind",
    "period_month": "period_month",
    "year": "year",
    "scenario": "scenario",
}

SALES_PLAN_EXECUTION_DIMENSION_COLUMNS = {
    "period_month": "snapshot_month",
    "period": "snapshot_month",
    "month": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "block_kind": "block_kind",
    "segment": "segment",
    "metric_key": "metric_key",
    "owner_scope": "owner_scope",
    "period_kind": "period_kind",
    "scenario": "scenario",
}


def sum_metric(metric_key: str) -> str:
    return f"SUM(CASE WHEN metric_key = '{metric_key}' THEN value END)"


def avg_metric(metric_key: str) -> str:
    return f"AVG(CASE WHEN metric_key = '{metric_key}' THEN value END)"


SALES_PLAN_EXECUTION_SQL_TEMPLATE = ReportSQLTemplate(
    table="sales_plan_execution_facts",
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "sales_plan_revenue": MetricSQLSpec(sum_metric("sales_revenue"), "sales_plan_revenue"),
        "sales_plan_cash_receipts": MetricSQLSpec(sum_metric("cash_receipts"), "sales_plan_cash_receipts"),
        "sales_plan_contract_area_sqm": MetricSQLSpec(sum_metric("contract_area_sqm"), "sales_plan_contract_area_sqm"),
        "sales_plan_contract_count": MetricSQLSpec(sum_metric("contract_count"), "sales_plan_contract_count"),
        "sales_plan_price_per_sqm": MetricSQLSpec(avg_metric("price_per_sqm"), "sales_plan_price_per_sqm"),
    },
    group_by_columns=SALES_PLAN_EXECUTION_GROUP_BY_COLUMNS,
    filter_columns=SALES_PLAN_EXECUTION_FILTER_COLUMNS,
    dimension_columns=SALES_PLAN_EXECUTION_DIMENSION_COLUMNS,
)
