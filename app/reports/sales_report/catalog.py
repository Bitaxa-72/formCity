from app.reports.common import MetricSpec


SALES_REPORT_PROJECTS = {"obvodny"}
SALES_REPORT_SEGMENTS = [
    "apartments",
    "commercial_1_floor",
    "restaurant",
    "storage",
    "commercial_2_floor",
    "sh",
]
SALES_REPORT_FILTERS = {
    "project",
    "period",
    "snapshot_month",
    "snapshot_date",
    "period_month",
    "segment",
    "metric_key",
    "owner_scope",
    "period_kind",
    "scenario",
}
SALES_REPORT_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "period_month",
    "segment",
    "metric_key",
    "owner_scope",
    "period_kind",
    "scenario",
}

SALES_REPORT_SUMMARY_METRICS = [
    "sales_contract_revenue",
    "sales_ddu_actual_payments",
    "sales_ddu_remaining_payment_schedule",
]
SALES_REPORT_SEGMENT_METRICS = [
    "sales_contract_revenue",
    "sales_contract_area_sqm",
    "sales_contract_count",
    "sales_price_per_sqm",
]

SALES_REPORT_METRICS = {
    "sales_contract_revenue": MetricSpec(
        unit="thousand_rub",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_contract_area_sqm": MetricSpec(
        unit="square_meter",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_contract_count": MetricSpec(
        unit="count",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_price_per_sqm": MetricSpec(
        unit="thousand_rub_per_square_meter",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_ddu_actual_payments": MetricSpec(
        unit="thousand_rub",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_ddu_remaining_payment_schedule": MetricSpec(
        unit="thousand_rub",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
    "sales_cumulative_price_per_sqm": MetricSpec(
        unit="thousand_rub_per_square_meter",
        group_by=SALES_REPORT_GROUP_BY,
        filters=SALES_REPORT_FILTERS,
        projects=SALES_REPORT_PROJECTS,
    ),
}
