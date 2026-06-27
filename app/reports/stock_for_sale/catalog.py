from app.reports.common import MetricSpec


STOCK_FOR_SALE_PROJECTS = {"obvodny"}
STOCK_FOR_SALE_FILTERS = {
    "project",
    "period",
    "snapshot_month",
    "snapshot_date",
    "row_type",
    "row_label",
    "row_label_contains",
    "property_type",
    "floor_number",
    "is_in_work",
}
STOCK_FOR_SALE_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "row_type",
    "row_label",
    "property_type",
    "floor_number",
    "is_in_work",
}

STOCK_FOR_SALE_DEFAULT_METRICS = [
    "stock_total_amount",
    "stock_area_sqm",
    "stock_unit_count",
    "stock_total_price_per_sqm",
]
STOCK_FOR_SALE_PRICE_METRICS = [
    "stock_ddu_price_per_sqm",
    "stock_dupt_price_per_sqm",
    "stock_total_price_per_sqm",
]
STOCK_FOR_SALE_AMOUNT_METRICS = [
    "stock_ddu_amount",
    "stock_dupt_markup_amount",
    "stock_total_amount",
]

STOCK_FOR_SALE_METRICS = {
    "stock_ddu_amount": MetricSpec(
        unit="rub",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_dupt_markup_amount": MetricSpec(
        unit="rub",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_total_amount": MetricSpec(
        unit="rub",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_area_sqm": MetricSpec(
        unit="square_meter",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_unit_count": MetricSpec(
        unit="count",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_ddu_price_per_sqm": MetricSpec(
        unit="rub_per_square_meter",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_dupt_price_per_sqm": MetricSpec(
        unit="rub_per_square_meter",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
    "stock_total_price_per_sqm": MetricSpec(
        unit="rub_per_square_meter",
        group_by=STOCK_FOR_SALE_GROUP_BY,
        filters=STOCK_FOR_SALE_FILTERS,
        projects=STOCK_FOR_SALE_PROJECTS,
    ),
}
