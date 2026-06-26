from typing import Any

from pydantic import BaseModel

from app.pipeline.metric_resolver import MetricResolution
from app.pipeline.query_frame import QueryFrame
from app.reports.registry import SQL_TEMPLATES
from app.reports.sql import ReportSQLTemplate


class SQLCompileError(Exception):
    pass


class SQLQuery(BaseModel):
    sql: str
    params: dict[str, Any]
    table: str
    metrics: list[str]
    group_by: list[str]


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
        if filter_name.endswith("_contains"):
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

    template = SQL_TEMPLATES.get(frame.report_type or "")
    if template is None:
        raise SQLCompileError("unknown_report_type")

    if frame.intent == "dimension_query":
        return compile_dimension_sql(frame, template)

    return compile_metric_sql(frame, metric_resolution, template)
