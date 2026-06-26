from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


ROADMAP_GROUP_BY_COLUMNS = {
    "row_order": "row_order",
    "step": "step_no",
    "parent_step": "parent_step_no",
    "action": "action_text",
    "external": "is_external",
    "total": "is_total",
    "period_month": "period_month",
}

ROADMAP_FILTER_COLUMNS = {
    "step_no": "step_no",
    "is_external": "is_external",
    "is_total": "is_total",
    "action_text_contains": "action_text",
}

ROADMAP_DIMENSION_COLUMNS = {
    "period_month": "period_month",
    "step": "step_no || '. ' || action_text",
    "external": "is_external",
}

ROADMAP_SQL_TEMPLATE = ReportSQLTemplate(
    table="roadmap_steps",
    date_column="period_month",
    project_column="project",
    metrics={
        "duration_min": MetricSQLSpec("MIN(min_work_days)", "duration_min"),
        "duration_max": MetricSQLSpec("MAX(max_work_days)", "duration_max"),
        "duration_range": MetricSQLSpec("MAX(max_work_days) - MIN(min_work_days)", "duration_range"),
        "step_count": MetricSQLSpec("COUNT(step_no)", "step_count"),
    },
    group_by_columns=ROADMAP_GROUP_BY_COLUMNS,
    filter_columns=ROADMAP_FILTER_COLUMNS,
    dimension_columns=ROADMAP_DIMENSION_COLUMNS,
)
