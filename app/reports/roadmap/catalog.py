from app.reports.common import MetricSpec


ROADMAP_GROUP_BY = {"row_order", "step", "parent_step", "action", "external", "total", "period_month"}
ROADMAP_FILTERS = {"project", "period", "step_no", "is_external", "is_total", "action_text_contains"}
ROADMAP_PROJECTS = {"all"}
ROADMAP_FULL_METRICS = ["duration_min", "duration_max"]

ROADMAP_METRICS = {
    "duration_min": MetricSpec(
        unit="work_day",
        group_by=ROADMAP_GROUP_BY,
        filters=ROADMAP_FILTERS,
        projects=ROADMAP_PROJECTS,
    ),
    "duration_max": MetricSpec(
        unit="work_day",
        group_by=ROADMAP_GROUP_BY,
        filters=ROADMAP_FILTERS,
        projects=ROADMAP_PROJECTS,
    ),
    "duration_range": MetricSpec(
        unit="work_day",
        group_by=ROADMAP_GROUP_BY,
        filters=ROADMAP_FILTERS,
        projects=ROADMAP_PROJECTS,
    ),
    "step_count": MetricSpec(
        unit="count",
        group_by={"period_month"},
        filters=ROADMAP_FILTERS,
        projects=ROADMAP_PROJECTS,
    ),
}
