from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


PAYMENT_CALENDAR_GROUP_BY_COLUMNS = {
    "project": "project",
    "period": "period_month",
    "month": "period_month",
    "metric": "article",
    "article": "article",
    "article_kind": "article_kind",
}

PAYMENT_CALENDAR_FILTER_COLUMNS = {
    "metric": "article",
    "article": "article",
    "article_kind": "article_kind",
}

PAYMENT_CALENDAR_DIMENSION_COLUMNS = {
    "article": "article",
    "article_kind": "article_kind",
    "project": "project",
    "period_month": "period_month",
}

PAYMENT_CALENDAR_SQL_TEMPLATE = ReportSQLTemplate(
    table="payment_calendar_facts",
    date_column="period_month",
    project_column="project",
    metrics={
        "plan": MetricSQLSpec("SUM(plan_amount)", "plan"),
        "fact": MetricSQLSpec("SUM(fact_amount)", "fact"),
        "deviation": MetricSQLSpec("SUM(deviation_amount)", "deviation"),
    },
    group_by_columns=PAYMENT_CALENDAR_GROUP_BY_COLUMNS,
    filter_columns=PAYMENT_CALENDAR_FILTER_COLUMNS,
    dimension_columns=PAYMENT_CALENDAR_DIMENSION_COLUMNS,
    context_metrics=["plan", "fact", "deviation"],
)
