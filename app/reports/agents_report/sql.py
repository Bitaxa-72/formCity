from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


AGENTS_REPORT_FACTS_TABLE_SQL = """
(
    SELECT
        project,
        snapshot_month,
        snapshot_date,
        'deals' AS source_kind,
        budget_month,
        NULL AS period_month,
        NULL AS value_kind,
        NULL AS period_kind,
        1 AS deal_count,
        area_sqm,
        commission_base_amount,
        commission_amount,
        act_total_amount,
        paid_amount,
        remaining_amount,
        ddu_assignment_amount,
        ddu_amount,
        assignment_amount,
        furniture_amount,
        NULL AS monthly_value
    FROM agents_report_deals
    UNION ALL
    SELECT
        project,
        snapshot_month,
        snapshot_date,
        'monthly' AS source_kind,
        NULL AS budget_month,
        period_month,
        value_kind,
        period_kind,
        0 AS deal_count,
        NULL AS area_sqm,
        NULL AS commission_base_amount,
        NULL AS commission_amount,
        NULL AS act_total_amount,
        NULL AS paid_amount,
        NULL AS remaining_amount,
        NULL AS ddu_assignment_amount,
        NULL AS ddu_amount,
        NULL AS assignment_amount,
        NULL AS furniture_amount,
        value AS monthly_value
    FROM agents_report_monthly_values
) AS agents_report_facts
""".strip()

AGENTS_REPORT_GROUP_BY_COLUMNS = {
    "month": "snapshot_month",
    "period": "period_month",
    "snapshot_month": "snapshot_month",
    "source_kind": "source_kind",
    "budget_month": "budget_month",
    "period_month": "period_month",
    "payment_period_month": "period_month",
    "value_kind": "value_kind",
    "period_kind": "period_kind",
}

AGENTS_REPORT_FILTER_COLUMNS = {
    "snapshot_month": "snapshot_month",
    "snapshot_date": "snapshot_date",
    "source_kind": "source_kind",
    "budget_month": "budget_month",
    "period_month": "period_month",
    "payment_period_month": "period_month",
    "value_kind": "value_kind",
    "period_kind": "period_kind",
}

AGENTS_REPORT_DIMENSION_COLUMNS = {
    "period_month": "snapshot_month",
    "period": "snapshot_month",
    "month": "snapshot_month",
    "snapshot_month": "snapshot_month",
    "source_kind": "source_kind",
    "budget_month": "budget_month",
    "payment_period_month": "period_month",
    "value_kind": "value_kind",
    "period_kind": "period_kind",
}


AGENTS_REPORT_SQL_TEMPLATE = ReportSQLTemplate(
    table=AGENTS_REPORT_FACTS_TABLE_SQL,
    date_column="snapshot_month",
    project_column="project",
    metrics={
        "agents_deal_count": MetricSQLSpec("SUM(deal_count)", "agents_deal_count"),
        "agents_area_sqm": MetricSQLSpec("SUM(area_sqm)", "agents_area_sqm"),
        "agents_commission_base_amount": MetricSQLSpec("SUM(commission_base_amount)", "agents_commission_base_amount"),
        "agents_commission_amount": MetricSQLSpec("SUM(commission_amount)", "agents_commission_amount"),
        "agents_act_total_amount": MetricSQLSpec("SUM(act_total_amount)", "agents_act_total_amount"),
        "agents_paid_amount": MetricSQLSpec("SUM(paid_amount)", "agents_paid_amount"),
        "agents_remaining_amount": MetricSQLSpec("SUM(remaining_amount)", "agents_remaining_amount"),
        "agents_ddu_assignment_amount": MetricSQLSpec("SUM(ddu_assignment_amount)", "agents_ddu_assignment_amount"),
        "agents_ddu_amount": MetricSQLSpec("SUM(ddu_amount)", "agents_ddu_amount"),
        "agents_assignment_amount": MetricSQLSpec("SUM(assignment_amount)", "agents_assignment_amount"),
        "agents_furniture_amount": MetricSQLSpec("SUM(furniture_amount)", "agents_furniture_amount"),
        "agents_monthly_value": MetricSQLSpec("SUM(monthly_value)", "agents_monthly_value"),
    },
    group_by_columns=AGENTS_REPORT_GROUP_BY_COLUMNS,
    filter_columns=AGENTS_REPORT_FILTER_COLUMNS,
    dimension_columns=AGENTS_REPORT_DIMENSION_COLUMNS,
)
