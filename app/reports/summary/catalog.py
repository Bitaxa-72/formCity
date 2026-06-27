from app.reports.common import MetricSpec


SUMMARY_PROJECTS = {"obvodny", "moskovsky", "evgenievsky", "all"}
SUMMARY_FILTERS = {
    "project",
    "source_file",
    "sheet_name",
    "sheet_kind",
    "row_type",
    "header_key",
    "header_key_contains",
    "header_label_contains",
    "is_sensitive",
}
SUMMARY_GROUP_BY = {
    "project",
    "source_file",
    "sheet_name",
    "sheet_kind",
    "row_type",
    "header_key",
}

SUMMARY_DEFAULT_METRICS = [
    "summary_sheet_count",
    "summary_row_count",
    "summary_cell_count",
]

SUMMARY_VALUE_METRICS = [
    "summary_numeric_cell_count",
    "summary_value_sum",
]

SUMMARY_METRICS = {
    "summary_sheet_count": MetricSpec(
        unit="count",
        group_by=SUMMARY_GROUP_BY,
        filters=SUMMARY_FILTERS,
        projects=SUMMARY_PROJECTS,
    ),
    "summary_row_count": MetricSpec(
        unit="count",
        group_by=SUMMARY_GROUP_BY,
        filters=SUMMARY_FILTERS,
        projects=SUMMARY_PROJECTS,
    ),
    "summary_cell_count": MetricSpec(
        unit="count",
        group_by=SUMMARY_GROUP_BY,
        filters=SUMMARY_FILTERS,
        projects=SUMMARY_PROJECTS,
    ),
    "summary_numeric_cell_count": MetricSpec(
        unit="count",
        group_by=SUMMARY_GROUP_BY,
        filters=SUMMARY_FILTERS,
        projects=SUMMARY_PROJECTS,
    ),
    "summary_value_sum": MetricSpec(
        unit="",
        group_by=SUMMARY_GROUP_BY,
        filters=SUMMARY_FILTERS,
        projects=SUMMARY_PROJECTS,
    ),
}
