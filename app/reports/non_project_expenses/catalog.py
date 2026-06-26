from app.reports.common import MetricSpec


NON_PROJECT_EXPENSES_PROJECTS = {"all"}
NON_PROJECT_EXPENSES_FILTERS = {
    "project",
    "period",
    "item_kind",
    "fm_category",
    "item_name",
    "item_name_contains",
    "row_type",
}
NON_PROJECT_EXPENSES_GROUP_BY = {
    "period",
    "month",
    "item_kind",
    "fm_category",
    "item_name",
    "row_type",
}

NON_PROJECT_EXPENSES_DEFAULT_METRICS = ["amount", "executed_amount", "remaining_amount"]

NON_PROJECT_EXPENSES_METRICS = {
    "amount": MetricSpec(
        unit="rub",
        group_by=NON_PROJECT_EXPENSES_GROUP_BY,
        filters=NON_PROJECT_EXPENSES_FILTERS,
        projects=NON_PROJECT_EXPENSES_PROJECTS,
    ),
    "executed_amount": MetricSpec(
        unit="rub",
        group_by=NON_PROJECT_EXPENSES_GROUP_BY,
        filters=NON_PROJECT_EXPENSES_FILTERS,
        projects=NON_PROJECT_EXPENSES_PROJECTS,
    ),
    "remaining_amount": MetricSpec(
        unit="rub",
        group_by=NON_PROJECT_EXPENSES_GROUP_BY,
        filters=NON_PROJECT_EXPENSES_FILTERS,
        projects=NON_PROJECT_EXPENSES_PROJECTS,
    ),
}
