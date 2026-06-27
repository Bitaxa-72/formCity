from app.reports.common import MetricSpec


DEBT_AND_BOOKINGS_PROJECTS = {"obvodny"}
DEBT_AND_BOOKINGS_FILTERS = {
    "project",
    "period",
    "snapshot_month",
    "snapshot_date",
    "period_month",
    "source_kind",
    "item_kind",
    "row_type",
    "section",
    "section_contains",
    "unit_number",
    "unit_number_contains",
    "unit_number_not_null",
    "status",
    "payment_type",
}
DEBT_AND_BOOKINGS_GROUP_BY = {
    "month",
    "period",
    "period_month",
    "snapshot_month",
    "source_kind",
    "item_kind",
    "row_type",
    "section",
    "unit_number",
    "status",
    "payment_type",
}

DEBT_AND_BOOKINGS_DEFAULT_METRICS = ["debt_item_count", "debt_total_amount"]
DEBT_AND_BOOKINGS_DEVIATION_METRICS = [
    "debt_plan_amount",
    "debt_updated_plan_amount",
    "debt_fact_payment_amount",
    "debt_remaining_amount",
]
DEBT_AND_BOOKINGS_REFUSAL_METRICS = [
    "debt_refusal_count",
    "debt_refusal_area",
    "debt_refusal_full_price",
]

DEBT_AND_BOOKINGS_METRICS = {
    "debt_item_count": MetricSpec(
        unit="count",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_total_amount": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_monthly_value": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_plan_amount": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_updated_plan_amount": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_fact_payment_amount": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_remaining_amount": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_refusal_count": MetricSpec(
        unit="count",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_refusal_area": MetricSpec(
        unit="square_meter",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
    "debt_refusal_full_price": MetricSpec(
        unit="rub",
        group_by=DEBT_AND_BOOKINGS_GROUP_BY,
        filters=DEBT_AND_BOOKINGS_FILTERS,
        projects=DEBT_AND_BOOKINGS_PROJECTS,
    ),
}
