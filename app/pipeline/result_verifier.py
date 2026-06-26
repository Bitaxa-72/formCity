from datetime import date
from typing import Any

from pydantic import BaseModel

from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.metric_resolver import MetricResolution
from app.pipeline.query_frame import QueryFrame


class ResultVerification(BaseModel):
    verified: bool
    errors: list[str]
    warnings: list[str]
    row_count: int
    metrics: list[str]
    columns: list[str]
    source: dict[str, Any]


def parse_date_value(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def collect_source(
    query_frame: QueryFrame,
    metric_resolution: MetricResolution,
    calculation_result: CalculationResult | None,
    missing_metrics: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "report_type": query_frame.report_type,
        "intent": query_frame.intent,
        "project": query_frame.project,
        "period": query_frame.period.model_dump(by_alias=True),
        "filters": query_frame.filters,
        "group_by": query_frame.group_by,
        "view": query_frame.view,
        "dimension": query_frame.dimension,
        "metrics": [metric.name for metric in metric_resolution.metrics] or (calculation_result.metrics if calculation_result else []),
        "units": {metric.name: metric.unit for metric in metric_resolution.metrics},
        "kind": calculation_result.kind if calculation_result else None,
        "missing_metrics": missing_metrics or [],
    }


def find_project_errors(query_frame: QueryFrame, calculation_result: CalculationResult) -> list[str]:
    if not query_frame.project or query_frame.project == "all":
        return []

    rows_with_project = [row for row in calculation_result.rows if "project" in row]
    if not rows_with_project:
        return []

    for row in rows_with_project:
        if row.get("project") != query_frame.project:
            return ["project_mismatch"]
    return []


def find_period_errors(query_frame: QueryFrame, calculation_result: CalculationResult) -> list[str]:
    period_from = parse_date_value(query_frame.period.from_date)
    period_to = parse_date_value(query_frame.period.to)
    if period_from is None and period_to is None:
        return []

    date_columns = {"period", "period_date", "period_month", "deal_date", "date"}
    for row in calculation_result.rows:
        for column in date_columns & set(row):
            value = parse_date_value(row[column])
            if value is None:
                continue
            if period_from and value < period_from:
                return ["period_out_of_range"]
            if period_to and value > period_to:
                return ["period_out_of_range"]
    return []


def find_metric_errors(metric_resolution: MetricResolution, calculation_result: CalculationResult) -> list[str]:
    expected_metrics = [metric.name for metric in metric_resolution.metrics]
    if not expected_metrics:
        return []

    missing = set(expected_metrics) - set(calculation_result.columns) - set(calculation_result.metrics)
    if missing:
        return ["metric_column_missing"]
    return []


def find_empty_result_errors(calculation_result: CalculationResult) -> list[str]:
    if calculation_result.row_count == 0:
        return ["empty_result"]

    if "source_rows" not in calculation_result.columns:
        return []

    source_rows = [
        row.get("source_rows")
        for row in calculation_result.rows
        if isinstance(row.get("source_rows"), int | float)
    ]
    if source_rows and all(value == 0 for value in source_rows):
        return ["empty_result"]
    return []


def find_missing_metric_values(metric_resolution: MetricResolution, calculation_result: CalculationResult) -> list[str]:
    missing = []
    for metric in metric_resolution.metrics:
        values = [
            row.get(metric.name)
            for row in calculation_result.rows
            if metric.name in row and row.get("source_rows", 1) != 0
        ]
        if values and all(value is None for value in values):
            missing.append(metric.name)
    return missing


def verify_result(
    query_frame: QueryFrame,
    metric_resolution: MetricResolution,
    calculation_result: CalculationResult | None,
) -> ResultVerification:
    if calculation_result is None:
        return ResultVerification(
            verified=False,
            errors=["result_missing"],
            warnings=[],
            row_count=0,
            metrics=[],
            columns=[],
            source=collect_source(query_frame, metric_resolution, None),
        )

    errors = []
    warnings = []

    errors.extend(find_empty_result_errors(calculation_result))
    errors.extend(find_metric_errors(metric_resolution, calculation_result))
    errors.extend(find_project_errors(query_frame, calculation_result))
    errors.extend(find_period_errors(query_frame, calculation_result))

    missing_metrics = find_missing_metric_values(metric_resolution, calculation_result)
    if missing_metrics:
        warnings.append("metric_value_missing")

    if not calculation_result.columns:
        warnings.append("columns_empty")

    unique_errors = list(dict.fromkeys(errors))
    unique_warnings = list(dict.fromkeys(warnings))

    return ResultVerification(
        verified=not unique_errors,
        errors=unique_errors,
        warnings=unique_warnings,
        row_count=calculation_result.row_count,
        metrics=calculation_result.metrics,
        columns=calculation_result.columns,
        source=collect_source(query_frame, metric_resolution, calculation_result, missing_metrics),
    )
