from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


SALES_REPORT_GROUP_BY_COLUMNS = {
    "month": "period_month",
    "period": "period_month",
    "period_month": "period_month",
    "snapshot_month": "snapshot_month",
    "segment": "segment",
    "metric_key": "metric_key",
    "owner_scope": "owner_scope",
    "period_kind": "period_kind",
    "scenario": "scenario",
}

SALES_REPORT_FILTER_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "snapshot_date": "snapshot_date",
    "period_month": "period_month",
    "segment": "segment",
    "metric_key": "metric_key",
    "owner_scope": "owner_scope",
    "period_kind": "period_kind",
    "scenario": "scenario",
}

SALES_REPORT_DIMENSION_COLUMNS = {
    "period_month": "period_month",
    "period": "period_month",
    "month": "period_month",
    "snapshot_month": "snapshot_month",
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


SALES_REPORT_SQL_TEMPLATE = ReportSQLTemplate(
    table="sales_report_facts",
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "sales_contract_revenue": MetricSQLSpec(sum_metric("contract_revenue"), "sales_contract_revenue"),
        "sales_contract_area_sqm": MetricSQLSpec(sum_metric("contract_area_sqm"), "sales_contract_area_sqm"),
        "sales_contract_count": MetricSQLSpec(sum_metric("contract_count"), "sales_contract_count"),
        "sales_price_per_sqm": MetricSQLSpec(avg_metric("price_per_sqm"), "sales_price_per_sqm"),
        "sales_ddu_actual_payments": MetricSQLSpec(sum_metric("ddu_actual_payments"), "sales_ddu_actual_payments"),
        "sales_ddu_remaining_payment_schedule": MetricSQLSpec(sum_metric("ddu_remaining_payment_schedule"), "sales_ddu_remaining_payment_schedule"),
        "sales_cumulative_price_per_sqm": MetricSQLSpec(avg_metric("cumulative_price_per_sqm"), "sales_cumulative_price_per_sqm"),
    },
    group_by_columns=SALES_REPORT_GROUP_BY_COLUMNS,
    filter_columns=SALES_REPORT_FILTER_COLUMNS,
    dimension_columns=SALES_REPORT_DIMENSION_COLUMNS,
)
