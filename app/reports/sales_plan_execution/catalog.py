from app.reports.common import MetricSpec


SALES_PLAN_EXECUTION_PROJECTS = {"obvodny"}
SALES_PLAN_EXECUTION_FILTERS = {
    "project",
    "period",
    "snapshot_month",
    "snapshot_date",
    "block_kind",
    "segment",
    "metric_key",
    "owner_scope",
    "period_kind",
    "period_month",
    "year",
    "scenario",
}
SALES_PLAN_EXECUTION_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "block_kind",
    "segment",
    "metric_key",
    "owner_scope",
    "period_kind",
    "period_month",
    "year",
    "scenario",
}

SALES_PLAN_EXECUTION_SUMMARY_METRICS = [
    "sales_plan_revenue",
    "sales_plan_cash_receipts",
    "sales_plan_contract_area_sqm",
    "sales_plan_contract_count",
]
SALES_PLAN_EXECUTION_SEGMENT_METRICS = [
    "sales_plan_revenue",
    "sales_plan_contract_area_sqm",
    "sales_plan_contract_count",
    "sales_plan_price_per_sqm",
]

SALES_PLAN_EXECUTION_METRICS = {
    "sales_plan_revenue": MetricSpec(
        unit="rub",
        group_by=SALES_PLAN_EXECUTION_GROUP_BY,
        filters=SALES_PLAN_EXECUTION_FILTERS,
        projects=SALES_PLAN_EXECUTION_PROJECTS,
    ),
    "sales_plan_cash_receipts": MetricSpec(
        unit="rub",
        group_by=SALES_PLAN_EXECUTION_GROUP_BY,
        filters=SALES_PLAN_EXECUTION_FILTERS,
        projects=SALES_PLAN_EXECUTION_PROJECTS,
    ),
    "sales_plan_contract_area_sqm": MetricSpec(
        unit="sqm",
        group_by=SALES_PLAN_EXECUTION_GROUP_BY,
        filters=SALES_PLAN_EXECUTION_FILTERS,
        projects=SALES_PLAN_EXECUTION_PROJECTS,
    ),
    "sales_plan_contract_count": MetricSpec(
        unit="count",
        group_by=SALES_PLAN_EXECUTION_GROUP_BY,
        filters=SALES_PLAN_EXECUTION_FILTERS,
        projects=SALES_PLAN_EXECUTION_PROJECTS,
    ),
    "sales_plan_price_per_sqm": MetricSpec(
        unit="rub_per_square_meter",
        group_by=SALES_PLAN_EXECUTION_GROUP_BY,
        filters=SALES_PLAN_EXECUTION_FILTERS,
        projects=SALES_PLAN_EXECUTION_PROJECTS,
    ),
}
