from app.reports.common import MetricSpec


MODEL_PROJECTS = {"obvodny"}
MODEL_FILTERS = {"project", "period", "scenario", "metric_key", "snapshot_month", "raw_sheet", "raw_query"}
MODEL_GROUP_BY = {"month", "metric", "snapshot_month"}
MODEL_RAW_VIEWS = {"model_raw_sheets", "model_raw_rows", "model_raw_search"}

MODEL_SUMMARY_METRICS = [
    "model_revenue",
    "model_cost_of_sales",
    "model_gross_profit",
    "model_net_profit",
    "model_npv",
]

MODEL_METRICS = {
    "model_revenue": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_cost_of_sales": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_gross_profit": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_net_profit": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_npv": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_roe": MetricSpec(unit="percent", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_llcr": MetricSpec(unit="ratio", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_total_area": MetricSpec(unit="square_meter", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_units_count": MetricSpec(unit="count", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_pir": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_pir_total": MetricSpec(unit="rub", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
    "model_pir_per_sqm": MetricSpec(unit="rub_per_square_meter", group_by=MODEL_GROUP_BY, filters=MODEL_FILTERS, projects=MODEL_PROJECTS),
}
