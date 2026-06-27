from app.reports.sql import MetricSQLSpec, ReportSQLTemplate


SUMMARY_FACTS_TABLE_SQL = """
(
    SELECT
        c.project,
        c.source_file,
        c.sheet_name,
        c.sheet_kind,
        c.row_number,
        r.row_type,
        r.period_label,
        c.header_key,
        c.header_label,
        c.value_type,
        c.value_number,
        c.is_sensitive
    FROM summary_cells c
    LEFT JOIN summary_rows r
      ON r.project = c.project
      AND r.source_file = c.source_file
      AND r.sheet_name = c.sheet_name
      AND r.row_number = c.row_number
) AS summary_facts
""".strip()

SUMMARY_GROUP_BY_COLUMNS = {
    "project": "project",
    "source_file": "source_file",
    "sheet_name": "sheet_name",
    "sheet_kind": "sheet_kind",
    "row_type": "row_type",
    "header_key": "header_key",
}

SUMMARY_FILTER_COLUMNS = {
    "source_file": "source_file",
    "sheet_name": "sheet_name",
    "sheet_kind": "sheet_kind",
    "row_type": "row_type",
    "header_key": "header_key",
    "header_key_contains": "header_key",
    "header_label_contains": "header_label",
    "is_sensitive": "is_sensitive",
}

SUMMARY_DIMENSION_COLUMNS = {
    "project": "project",
    "source_file": "source_file",
    "sheet_name": "sheet_name",
    "sheet_kind": "sheet_kind",
    "row_type": "row_type",
    "header_key": "header_key",
}

SUMMARY_SQL_TEMPLATE = ReportSQLTemplate(
    table=SUMMARY_FACTS_TABLE_SQL,
    date_column="source_file",
    project_column="project",
    metrics={
        "summary_sheet_count": MetricSQLSpec("COUNT(DISTINCT source_file || '|' || sheet_name)", "summary_sheet_count"),
        "summary_row_count": MetricSQLSpec("COUNT(DISTINCT source_file || '|' || sheet_name || '|' || row_number)", "summary_row_count"),
        "summary_cell_count": MetricSQLSpec("COUNT(*)", "summary_cell_count"),
        "summary_numeric_cell_count": MetricSQLSpec("SUM(CASE WHEN value_number IS NOT NULL AND is_sensitive = 0 THEN 1 ELSE 0 END)", "summary_numeric_cell_count"),
        "summary_value_sum": MetricSQLSpec("SUM(CASE WHEN value_number IS NOT NULL AND is_sensitive = 0 THEN value_number ELSE 0 END)", "summary_value_sum"),
    },
    group_by_columns=SUMMARY_GROUP_BY_COLUMNS,
    filter_columns=SUMMARY_FILTER_COLUMNS,
    dimension_columns=SUMMARY_DIMENSION_COLUMNS,
)
