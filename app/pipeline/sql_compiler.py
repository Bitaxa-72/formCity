from typing import Any

from pydantic import BaseModel

from app.pipeline.metric_resolver import MetricResolution
from app.pipeline.query_frame import QueryFrame
from app.reports.model.catalog import MODEL_RAW_VIEWS
from app.reports.registry import SQL_TEMPLATES
from app.reports.sql import ReportSQLTemplate
from app.reports.summary.catalog import SUMMARY_RAW_VIEWS


class SQLCompileError(Exception):
    pass


class SQLQuery(BaseModel):
    sql: str
    params: dict[str, Any]
    table: str
    metrics: list[str]
    group_by: list[str]


RAW_SHEET_ALIASES = {
    "consolidation": "consolidation",
    "для консолидации": "consolidation",
    "консолидация": "consolidation",
    "financial_model": "financial_model",
    "финмодель": "financial_model",
    "фин модель": "financial_model",
    "финансовая модель": "financial_model",
    "remains": "remains",
    "остатки": "remains",
    "остаток": "remains",
    "fm": "fm",
    "фм": "fm",
    "фм_": "fm",
    "fm_plan": "fm_plan",
    "фм план": "fm_plan",
    "фм_план": "fm_plan",
    "newkpi": "newkpi",
    "newkpi's": "newkpi",
    "newkpi_plan": "newkpi_plan",
    "newkpi план": "newkpi_plan",
    "newkpi's план": "newkpi_plan",
    "passport": "passport",
    "паспорт": "passport",
    "rates": "rates",
    "проценты": "rates",
    "comparison": "comparison",
    "сравнение": "comparison",
}


def normalize_raw_sheet(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().lower().replace("ё", "е").split())
    return RAW_SHEET_ALIASES.get(normalized)


def append_model_raw_common_filters(frame: QueryFrame, alias: str, where_parts: list[str], params: dict[str, Any]) -> None:
    if frame.project and frame.project != "all":
        where_parts.append(f"{alias}.project = :project")
        params["project"] = frame.project
    if frame.period.from_date:
        where_parts.append(f"{alias}.snapshot_month >= :date_from")
        params["date_from"] = frame.period.from_date
    if frame.period.to:
        where_parts.append(f"{alias}.snapshot_month <= :date_to")
        params["date_to"] = frame.period.to

    sheet_kind = normalize_raw_sheet(frame.filters.get("raw_sheet"))
    if sheet_kind:
        where_parts.append(f"{alias}.sheet_kind = :raw_sheet")
        params["raw_sheet"] = sheet_kind


def compile_model_raw_sheets_sql(frame: QueryFrame) -> SQLQuery:
    where_parts: list[str] = []
    params: dict[str, Any] = {}
    append_model_raw_common_filters(frame, "s", where_parts, params)
    where_sql = "\nWHERE " + "\n  AND ".join(where_parts) if where_parts else ""
    return SQLQuery(
        sql=(
            "SELECT DISTINCT\n"
            "  s.sheet_name AS raw_sheet,\n"
            "  s.row_count AS row_count,\n"
            "  s.cell_count AS cell_count\n"
            "FROM model_raw_sheets s"
            f"{where_sql}\n"
            "ORDER BY s.sheet_name"
        ),
        params=params,
        table="model_raw_sheets",
        metrics=[],
        group_by=["raw_sheet"],
    )


def compile_model_raw_rows_sql(frame: QueryFrame) -> SQLQuery:
    where_parts = ["r.is_sensitive = 0"]
    params: dict[str, Any] = {}
    append_model_raw_common_filters(frame, "r", where_parts, params)

    raw_query = frame.filters.get("raw_query")
    if isinstance(raw_query, str) and raw_query.strip():
        where_parts.append(
            "(\n"
            "    r.row_label LIKE :raw_query\n"
            "    OR EXISTS (\n"
            "      SELECT 1\n"
            "      FROM model_raw_cells sc\n"
            "      WHERE sc.project = r.project\n"
            "        AND sc.snapshot_month = r.snapshot_month\n"
            "        AND sc.source_file = r.source_file\n"
            "        AND sc.sheet_name = r.sheet_name\n"
            "        AND sc.row_number = r.row_number\n"
            "        AND sc.is_sensitive = 0\n"
            "        AND sc.value_text LIKE :raw_query\n"
            "    )\n"
            "  )",
        )
        params["raw_query"] = f"%{raw_query.strip()}%"

    where_sql = "\nWHERE " + "\n  AND ".join(where_parts)
    return SQLQuery(
        sql=(
            "SELECT\n"
            "  r.sheet_name AS raw_sheet,\n"
            "  r.row_number AS row_number,\n"
            "  r.row_label AS row_label,\n"
            "  COUNT(c.id) AS visible_cells,\n"
            "  GROUP_CONCAT(\n"
            "    c.column_letter || ': ' || COALESCE(c.value_text, CAST(c.value_number AS TEXT), c.value_date, CAST(c.value_bool AS TEXT)),\n"
            "    ' | '\n"
            "  ) AS values_preview\n"
            "FROM model_raw_rows r\n"
            "LEFT JOIN model_raw_cells c\n"
            "  ON c.project = r.project\n"
            "  AND c.snapshot_month = r.snapshot_month\n"
            "  AND c.source_file = r.source_file\n"
            "  AND c.sheet_name = r.sheet_name\n"
            "  AND c.row_number = r.row_number\n"
            "  AND c.is_sensitive = 0"
            f"{where_sql}\n"
            "GROUP BY r.sheet_name, r.row_number, r.row_label\n"
            "ORDER BY r.sheet_name, r.row_number"
        ),
        params=params,
        table="model_raw_rows",
        metrics=[],
        group_by=["raw_row"],
    )


def compile_model_raw_sql(frame: QueryFrame) -> SQLQuery:
    if frame.view == "model_raw_sheets":
        return compile_model_raw_sheets_sql(frame)
    if frame.view in {"model_raw_rows", "model_raw_search"}:
        return compile_model_raw_rows_sql(frame)
    raise SQLCompileError("unknown_model_raw_view")


def append_summary_common_filters(frame: QueryFrame, where_parts: list[str], params: dict[str, Any]) -> None:
    if frame.project and frame.project != "all":
        where_parts.append("r.project = :project")
        params["project"] = frame.project

    simple_filters = {
        "source_file": "r.source_file",
        "sheet_name": "r.sheet_name",
        "sheet_kind": "r.sheet_kind",
        "row_type": "r.row_type",
        "header_key": "c.header_key",
    }
    contains_filters = {
        "header_key_contains": "c.header_key",
        "header_label_contains": "c.header_label",
        "row_label_contains": "r.row_label",
        "value_text_contains": "c.value_text",
    }
    for name, column in simple_filters.items():
        value = frame.filters.get(name)
        if value is not None:
            where_parts.append(f"{column} = :{name}")
            params[name] = value
    for name, column in contains_filters.items():
        value = frame.filters.get(name)
        if isinstance(value, str) and value.strip():
            where_parts.append(f"{column} LIKE :{name}")
            params[name] = f"%{value.strip()}%"


def compile_summary_raw_rows_sql(frame: QueryFrame) -> SQLQuery:
    where_parts = ["c.is_sensitive = 0"]
    params: dict[str, Any] = {}
    append_summary_common_filters(frame, where_parts, params)

    raw_query = frame.filters.get("raw_query")
    if isinstance(raw_query, str) and raw_query.strip():
        where_parts.append(
            "(\n"
            "    r.row_label LIKE :raw_query\n"
            "    OR c.header_label LIKE :raw_query\n"
            "    OR c.value_text LIKE :raw_query\n"
            "  )",
        )
        params["raw_query"] = f"%{raw_query.strip()}%"

    where_sql = "\nWHERE " + "\n  AND ".join(where_parts)
    return SQLQuery(
        sql=(
            "SELECT\n"
            "  r.project AS project,\n"
            "  r.source_file AS source_file,\n"
            "  r.sheet_name AS sheet_name,\n"
            "  r.sheet_kind AS sheet_kind,\n"
            "  r.row_number AS row_number,\n"
            "  r.row_type AS row_type,\n"
            "  r.row_label AS row_label,\n"
            "  r.period_label AS period_label,\n"
            "  r.unit_number AS unit_number,\n"
            "  COUNT(c.id) AS visible_cells,\n"
            "  GROUP_CONCAT(\n"
            "    COALESCE(c.header_label, c.column_letter) || ': ' || COALESCE(c.value_text, CAST(c.value_number AS TEXT), c.value_date, CAST(c.value_bool AS TEXT)),\n"
            "    ' | '\n"
            "  ) AS values_preview\n"
            "FROM summary_rows r\n"
            "JOIN summary_cells c\n"
            "  ON c.project = r.project\n"
            "  AND c.source_file = r.source_file\n"
            "  AND c.sheet_name = r.sheet_name\n"
            "  AND c.row_number = r.row_number"
            f"{where_sql}\n"
            "GROUP BY r.project, r.source_file, r.sheet_name, r.sheet_kind, r.row_number, r.row_type, r.row_label, r.period_label, r.unit_number\n"
            "ORDER BY r.project, r.source_file, r.sheet_name, r.row_number"
        ),
        params=params,
        table="summary_rows",
        metrics=[],
        group_by=["summary_row"],
    )


def compile_summary_raw_sql(frame: QueryFrame) -> SQLQuery:
    if frame.view in SUMMARY_RAW_VIEWS:
        return compile_summary_raw_rows_sql(frame)
    raise SQLCompileError("unknown_summary_raw_view")


def build_filter_clause(column: str, param_name: str, value: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(value, list):
        if not value:
            raise SQLCompileError("empty_filter_value")
        placeholders = []
        params = {}
        for index, item in enumerate(value):
            item_param_name = f"{param_name}_{index}"
            placeholders.append(f":{item_param_name}")
            params[item_param_name] = item
        return f"{column} IN ({', '.join(placeholders)})", params

    return f"{column} = :{param_name}", {param_name: value}


def build_contains_filter_clause(column: str, param_name: str, value: Any) -> tuple[str, dict[str, Any]]:
    if not isinstance(value, str) or not value.strip():
        raise SQLCompileError("empty_filter_value")
    return f"{column} LIKE :{param_name}", {param_name: f'%{value.strip()}%'}


def build_not_null_filter_clause(column: str) -> tuple[str, dict[str, Any]]:
    return f"({column} IS NOT NULL AND {column} != '')", {}


def collect_where_parts(frame: QueryFrame, template: ReportSQLTemplate) -> tuple[list[str], dict[str, Any]]:
    where_parts = []
    params: dict[str, Any] = {}

    if frame.project and frame.project != "all":
        where_parts.append(f"{template.project_column} = :project")
        params["project"] = frame.project

    if frame.period.from_date:
        where_parts.append(f"{template.date_column} >= :date_from")
        params["date_from"] = frame.period.from_date
    if frame.period.to:
        where_parts.append(f"{template.date_column} <= :date_to")
        params["date_to"] = frame.period.to

    for filter_name, value in frame.filters.items():
        if filter_name in {"project", "period"}:
            continue
        column = template.filter_columns.get(filter_name)
        if column is None:
            raise SQLCompileError("unknown_filter")
        if filter_name.endswith("_not_null"):
            clause, filter_params = build_not_null_filter_clause(column)
        elif filter_name.endswith("_contains"):
            clause, filter_params = build_contains_filter_clause(column, f"filter_{filter_name}", value)
        else:
            clause, filter_params = build_filter_clause(column, f"filter_{filter_name}", value)
        where_parts.append(clause)
        params.update(filter_params)

    return where_parts, params


def compile_dimension_sql(frame: QueryFrame, template: ReportSQLTemplate) -> SQLQuery:
    if not frame.dimension:
        raise SQLCompileError("empty_dimension")

    column = template.dimension_columns.get(frame.dimension)
    if column is None:
        raise SQLCompileError("unknown_dimension")

    where_parts, params = collect_where_parts(frame, template)

    sql_parts = [
        "SELECT DISTINCT",
        f"  {column} AS {frame.dimension}",
        f"FROM {template.table}",
    ]
    if where_parts:
        sql_parts.append("WHERE " + "\n  AND ".join(where_parts))
    sql_parts.append(f"ORDER BY {column}")

    return SQLQuery(
        sql="\n".join(sql_parts),
        params=params,
        table=template.table,
        metrics=[],
        group_by=[frame.dimension],
    )


def compile_metric_sql(frame: QueryFrame, metric_resolution: MetricResolution, template: ReportSQLTemplate) -> SQLQuery:
    if not metric_resolution.metrics:
        raise SQLCompileError("empty_metrics")

    group_columns = []
    for group_by in frame.group_by:
        column = template.group_by_columns.get(group_by)
        if column is None:
            raise SQLCompileError("unknown_group_by")
        group_columns.append((group_by, column))

    requested_metric_names = [metric.name for metric in metric_resolution.metrics]
    selected_metric_names = list(requested_metric_names)
    if template.context_metrics:
        selected_metric_names = list(dict.fromkeys(selected_metric_names + template.context_metrics))

    metric_selects = []
    for metric_name in selected_metric_names:
        spec = template.metrics.get(metric_name)
        if spec is None:
            raise SQLCompileError("unknown_metric")
        metric_selects.append(f"{spec.expression} AS {spec.alias}")
    metric_selects.append("COUNT(*) AS source_rows")

    select_parts = [f"{column} AS {name}" for name, column in group_columns] + metric_selects
    where_parts, params = collect_where_parts(frame, template)

    sql_parts = [
        "SELECT",
        "  " + ",\n  ".join(select_parts),
        f"FROM {template.table}",
    ]
    if where_parts:
        sql_parts.append("WHERE " + "\n  AND ".join(where_parts))
    if group_columns:
        sql_parts.append("GROUP BY " + ", ".join(column for _, column in group_columns))
        if any(name == "row_order" for name, _ in group_columns):
            sql_parts.append("ORDER BY row_order")

    return SQLQuery(
        sql="\n".join(sql_parts),
        params=params,
        table=template.table,
        metrics=requested_metric_names,
        group_by=frame.group_by,
    )


def compile_sql(frame: QueryFrame, metric_resolution: MetricResolution) -> SQLQuery:
    if not frame.ready:
        raise SQLCompileError("query_frame_not_ready")
    if not metric_resolution.valid:
        raise SQLCompileError("metric_resolution_not_valid")
    if frame.operation:
        raise SQLCompileError("operation_query_not_supported")

    if frame.report_type == "model" and frame.view in MODEL_RAW_VIEWS:
        return compile_model_raw_sql(frame)
    if frame.report_type == "summary" and frame.view in SUMMARY_RAW_VIEWS:
        return compile_summary_raw_sql(frame)

    template = SQL_TEMPLATES.get(frame.report_type or "")
    if template is None:
        raise SQLCompileError("unknown_report_type")

    if frame.intent == "dimension_query":
        return compile_dimension_sql(frame, template)

    return compile_metric_sql(frame, metric_resolution, template)
