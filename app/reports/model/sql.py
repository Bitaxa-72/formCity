from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


MODEL_FACTS_TABLE_SQL = """
(
    SELECT
        project,
        snapshot_month,
        scenario,
        metric_name,
        metric_key,
        normalized_value
    FROM model_kpi_facts
    WHERE is_sensitive = 0
    UNION ALL
    SELECT
        project,
        snapshot_month,
        'current' AS scenario,
        metric_name,
        metric_key,
        current_value AS normalized_value
    FROM model_comparison_facts
    WHERE is_sensitive = 0
    UNION ALL
    SELECT
        project,
        snapshot_month,
        'current' AS scenario,
        metric_name,
        metric_key,
        value_number AS normalized_value
    FROM model_passport_facts
    WHERE is_sensitive = 0
) AS model_metric_facts
""".strip()

MODEL_GROUP_BY_COLUMNS = {
    "month": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "metric": "metric_name",
}

MODEL_FILTER_COLUMNS = {
    "scenario": "scenario",
    "metric_key": "metric_key",
    "snapshot_month": "snapshot_month",
}

MODEL_DIMENSION_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "metric": "metric_name",
}


def kpi_metric(metric_key: str) -> MetricSQLSpec:
    return MetricSQLSpec(f"MAX(CASE WHEN metric_key = '{metric_key}' THEN normalized_value END)", metric_key)


def kpi_sum_metric(metric_key: str) -> MetricSQLSpec:
    expression = (
        f"CASE WHEN SUM(CASE WHEN metric_key = '{metric_key}' THEN 1 ELSE 0 END) = 0 "
        f"THEN NULL ELSE SUM(CASE WHEN metric_key = '{metric_key}' THEN COALESCE(normalized_value, 0) ELSE 0 END) END"
    )
    return MetricSQLSpec(expression, metric_key)


def kpi_metric_by_sign(metric_key: str, positive: bool, alias: str) -> MetricSQLSpec:
    sign_filter = ">= 0" if positive else "< 0"
    expression = f"MAX(CASE WHEN metric_key = '{metric_key}' AND normalized_value {sign_filter} THEN normalized_value END)"
    return MetricSQLSpec(expression, alias)


MODEL_SQL_TEMPLATE = ReportSQLTemplate(
    table=MODEL_FACTS_TABLE_SQL,
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "model_revenue": kpi_metric("model_revenue"),
        "model_cost_of_sales": kpi_metric("model_cost_of_sales"),
        "model_gross_profit": kpi_metric("model_gross_profit"),
        "model_net_profit": kpi_metric("model_net_profit"),
        "model_npv": kpi_metric("model_npv"),
        "model_roe": kpi_metric("model_roe"),
        "model_llcr": kpi_metric("model_llcr"),
        "model_total_area": kpi_metric("model_total_area"),
        "model_units_count": kpi_sum_metric("model_units_count"),
        "model_pir": kpi_metric("model_pir"),
        "model_pir_total": kpi_metric_by_sign("model_pir", positive=False, alias="model_pir_total"),
        "model_pir_per_sqm": kpi_metric_by_sign("model_pir", positive=True, alias="model_pir_per_sqm"),
    },
    group_by_columns=MODEL_GROUP_BY_COLUMNS,
    filter_columns=MODEL_FILTER_COLUMNS,
    dimension_columns=MODEL_DIMENSION_COLUMNS,
)
