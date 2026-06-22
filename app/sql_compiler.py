from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from app.metric_resolver import MetricResolution
from app.query_frame import QueryFrame


class SQLCompileError(Exception):
    pass


class SQLQuery(BaseModel):
    sql: str
    params: dict[str, Any]
    table: str
    metrics: list[str]
    group_by: list[str]


@dataclass(frozen=True)
class MetricSQLSpec:
    expression: str
    alias: str


@dataclass(frozen=True)
class ReportSQLTemplate:
    table: str
    date_column: str
    project_column: str
    metrics: dict[str, MetricSQLSpec]
    group_by_columns: dict[str, str]
    filter_columns: dict[str, str]


COMMON_GROUP_BY_COLUMNS = {
    "project": "project",
    "period": "period_date",
    "month": "month",
    "quarter": "quarter",
    "year": "year",
    "floor": "floor",
    "room_type": "room_type",
    "agent": "agent_id",
    "bank": "bank",
    "metric": "metric_name",
}

COMMON_FILTER_COLUMNS = {
    "room_type": "room_type",
    "agent": "agent_id",
    "bank": "bank",
    "metric": "metric_name",
}

SQL_TEMPLATES = {
    "summary": ReportSQLTemplate(
        table="summary_facts",
        date_column="period_date",
        project_column="project",
        metrics={
            "revenue": MetricSQLSpec("SUM(revenue_amount)", "revenue"),
            "sold_area": MetricSQLSpec("SUM(sold_area)", "sold_area"),
            "deal_count": MetricSQLSpec("COUNT(deal_id)", "deal_count"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
    "sales_report": ReportSQLTemplate(
        table="sales_facts",
        date_column="deal_date",
        project_column="project",
        metrics={
            "revenue": MetricSQLSpec("SUM(revenue_amount)", "revenue"),
            "sold_area": MetricSQLSpec("SUM(sold_area)", "sold_area"),
            "deal_count": MetricSQLSpec("COUNT(deal_id)", "deal_count"),
            "average_deal_price": MetricSQLSpec("AVG(deal_price)", "average_deal_price"),
            "price_per_square_meter": MetricSQLSpec("AVG(price_per_square_meter)", "price_per_square_meter"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
    "payment_calendar": ReportSQLTemplate(
        table="payment_calendar_facts",
        date_column="period_date",
        project_column="project",
        metrics={
            "plan": MetricSQLSpec("SUM(plan_amount)", "plan"),
            "fact": MetricSQLSpec("SUM(fact_amount)", "fact"),
            "deviation": MetricSQLSpec("SUM(deviation_amount)", "deviation"),
            "remaining_amount": MetricSQLSpec("SUM(remaining_amount)", "remaining_amount"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
    "agents_report": ReportSQLTemplate(
        table="agent_facts",
        date_column="deal_date",
        project_column="project",
        metrics={
            "deal_count": MetricSQLSpec("COUNT(deal_id)", "deal_count"),
            "agent_commission": MetricSQLSpec("SUM(agent_commission_amount)", "agent_commission"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
    "debt_and_bookings": ReportSQLTemplate(
        table="debt_booking_facts",
        date_column="period_date",
        project_column="project",
        metrics={
            "debt": MetricSQLSpec("SUM(debt_amount)", "debt"),
            "booking_amount": MetricSQLSpec("SUM(booking_amount)", "booking_amount"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
    "roadmap": ReportSQLTemplate(
        table="roadmap_facts",
        date_column="period_date",
        project_column="project",
        metrics={
            "pledge_release_amount": MetricSQLSpec("SUM(pledge_release_amount)", "pledge_release_amount"),
        },
        group_by_columns=COMMON_GROUP_BY_COLUMNS,
        filter_columns=COMMON_FILTER_COLUMNS,
    ),
}


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


def compile_sql(frame: QueryFrame, metric_resolution: MetricResolution) -> SQLQuery:
    if not frame.ready:
        raise SQLCompileError("query_frame_not_ready")
    if not metric_resolution.valid:
        raise SQLCompileError("metric_resolution_not_valid")
    if frame.operation:
        raise SQLCompileError("operation_query_not_supported")
    if not metric_resolution.metrics:
        raise SQLCompileError("empty_metrics")

    template = SQL_TEMPLATES.get(frame.report_type or "")
    if template is None:
        raise SQLCompileError("unknown_report_type")

    group_columns = []
    for group_by in frame.group_by:
        column = template.group_by_columns.get(group_by)
        if column is None:
            raise SQLCompileError("unknown_group_by")
        group_columns.append((group_by, column))

    metric_selects = []
    for metric in metric_resolution.metrics:
        spec = template.metrics.get(metric.name)
        if spec is None:
            raise SQLCompileError("unknown_metric")
        metric_selects.append(f"{spec.expression} AS {spec.alias}")

    select_parts = [f"{column} AS {name}" for name, column in group_columns] + metric_selects
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
        clause, filter_params = build_filter_clause(column, f"filter_{filter_name}", value)
        where_parts.append(clause)
        params.update(filter_params)

    sql_parts = [
        "SELECT",
        "  " + ",\n  ".join(select_parts),
        f"FROM {template.table}",
    ]
    if where_parts:
        sql_parts.append("WHERE " + "\n  AND ".join(where_parts))
    if group_columns:
        sql_parts.append("GROUP BY " + ", ".join(column for _, column in group_columns))

    return SQLQuery(
        sql="\n".join(sql_parts),
        params=params,
        table=template.table,
        metrics=[metric.name for metric in metric_resolution.metrics],
        group_by=frame.group_by,
    )
