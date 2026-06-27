from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


STOCK_FOR_SALE_GROUP_BY_COLUMNS = {
    "month": "snapshot_month",
    "period": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "row_type": "row_type",
    "row_label": "row_label",
    "property_type": "property_type",
    "floor_number": "floor_number",
    "is_in_work": "is_in_work",
}

STOCK_FOR_SALE_FILTER_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "snapshot_date": "snapshot_date",
    "row_type": "row_type",
    "row_label": "row_label",
    "row_label_contains": "row_label",
    "property_type": "property_type",
    "floor_number": "floor_number",
    "is_in_work": "is_in_work",
}

STOCK_FOR_SALE_DIMENSION_COLUMNS = {
    "period_month": "snapshot_month",
    "period": "snapshot_month",
    "month": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "row_type": "row_type",
    "row_label": "row_label",
    "property_type": "property_type",
    "floor_number": "floor_number",
}


STOCK_FOR_SALE_SQL_TEMPLATE = ReportSQLTemplate(
    table="stock_for_sale_facts",
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "stock_ddu_amount": MetricSQLSpec("SUM(ddu_amount)", "stock_ddu_amount"),
        "stock_dupt_markup_amount": MetricSQLSpec("SUM(dupt_markup_amount)", "stock_dupt_markup_amount"),
        "stock_total_amount": MetricSQLSpec("SUM(total_amount)", "stock_total_amount"),
        "stock_area_sqm": MetricSQLSpec("SUM(area_sqm)", "stock_area_sqm"),
        "stock_unit_count": MetricSQLSpec("SUM(unit_count)", "stock_unit_count"),
        "stock_ddu_price_per_sqm": MetricSQLSpec("AVG(ddu_price_per_sqm)", "stock_ddu_price_per_sqm"),
        "stock_dupt_price_per_sqm": MetricSQLSpec("AVG(dupt_price_per_sqm)", "stock_dupt_price_per_sqm"),
        "stock_total_price_per_sqm": MetricSQLSpec("AVG(total_price_per_sqm)", "stock_total_price_per_sqm"),
    },
    group_by_columns=STOCK_FOR_SALE_GROUP_BY_COLUMNS,
    filter_columns=STOCK_FOR_SALE_FILTER_COLUMNS,
    dimension_columns=STOCK_FOR_SALE_DIMENSION_COLUMNS,
)
