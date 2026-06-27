from app.reports.common import MetricSpec


AGENTS_REPORT_PROJECTS = {"obvodny"}
AGENTS_REPORT_FILTERS = {
    "project",
    "period",
    "snapshot_month",
    "snapshot_date",
    "source_kind",
    "agent",
    "agent_contains",
    "unit_number",
    "unit_number_contains",
    "budget_month",
    "period_month",
    "payment_period_month",
    "value_kind",
    "period_kind",
}
AGENTS_REPORT_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "source_kind",
    "agent",
    "unit_number",
    "budget_month",
    "period_month",
    "payment_period_month",
    "value_kind",
    "period_kind",
}

AGENTS_REPORT_DEFAULT_METRICS = [
    "agents_deal_count",
    "agents_commission_amount",
    "agents_paid_amount",
    "agents_remaining_amount",
]
AGENTS_REPORT_DDU_METRICS = [
    "agents_ddu_assignment_amount",
    "agents_ddu_amount",
    "agents_assignment_amount",
    "agents_furniture_amount",
]

AGENTS_REPORT_METRICS = {
    "agents_deal_count": MetricSpec(
        unit="count",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_area_sqm": MetricSpec(
        unit="square_meter",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_commission_base_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_commission_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_act_total_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_paid_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_remaining_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_ddu_assignment_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_ddu_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_assignment_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_furniture_amount": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
    "agents_monthly_value": MetricSpec(
        unit="rub",
        group_by=AGENTS_REPORT_GROUP_BY,
        filters=AGENTS_REPORT_FILTERS,
        projects=AGENTS_REPORT_PROJECTS,
    ),
}
