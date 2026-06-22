from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.query_frame import QueryFrame
from app.sql_compiler import SQLQuery


class CalculationError(Exception):
    pass


class CalculationResult(BaseModel):
    kind: str
    rows: list[dict[str, Any]]
    row_count: int
    metrics: list[str]
    columns: list[str]
    operation: dict[str, Any] | None = None


class CalculationEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate(
        self,
        query_frame: QueryFrame,
        sql_query: SQLQuery | None,
        last_result: dict[str, Any] | None,
    ) -> CalculationResult:
        return calculate_query(self.db, query_frame, sql_query, last_result)


def normalize_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if isinstance(value, float):
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_value(value) for key, value in row.items()}


def execute_sql_query(db: Session, sql_query: SQLQuery) -> CalculationResult:
    try:
        result = db.execute(text(sql_query.sql), sql_query.params)
    except SQLAlchemyError as error:
        raise CalculationError("sql_execution_failed") from error

    rows = [normalize_row(dict(row)) for row in result.mappings().all()]
    columns = list(rows[0]) if rows else []

    return CalculationResult(
        kind="sql_result",
        rows=rows,
        row_count=len(rows),
        metrics=sql_query.metrics,
        columns=columns,
    )


def find_metric_value(data: Any, metric: str) -> int | float:
    if isinstance(data, dict):
        if metric in data and isinstance(data[metric], int | float):
            return data[metric]

        metrics = data.get("metrics")
        if isinstance(metrics, dict) and isinstance(metrics.get(metric), int | float):
            return metrics[metric]

        rows = data.get("rows")
        if isinstance(rows, list) and rows:
            first_row = rows[0]
            if isinstance(first_row, dict) and isinstance(first_row.get(metric), int | float):
                return first_row[metric]

    raise CalculationError("metric_value_not_found")


def resolve_operand_value(operand: dict[str, Any] | None, last_result: dict[str, Any] | None) -> int | float:
    if not operand:
        raise CalculationError("operation_operand_missing")

    source = operand.get("source")
    if source == "literal":
        value = operand.get("value")
        if isinstance(value, int | float):
            return value
        raise CalculationError("literal_value_not_numeric")

    if source == "last_result":
        if last_result is None:
            raise CalculationError("last_result_missing")
        metric = operand.get("metric")
        if not isinstance(metric, str):
            raise CalculationError("metric_name_missing")
        return find_metric_value(last_result, metric)

    raise CalculationError("operation_source_not_supported")


def calculate_operation(operation: dict[str, Any], last_result: dict[str, Any] | None) -> CalculationResult:
    operation_type = operation.get("type")
    left = resolve_operand_value(operation.get("left"), last_result)
    right = resolve_operand_value(operation.get("right"), last_result) if operation.get("right") else None

    if operation_type == "add":
        value = left + require_right(right)
    elif operation_type == "subtract":
        value = left - require_right(right)
    elif operation_type == "multiply":
        value = left * require_right(right)
    elif operation_type == "divide":
        divisor = require_right(right)
        if divisor == 0:
            raise CalculationError("division_by_zero")
        value = left / divisor
    elif operation_type == "percent":
        divisor = require_right(right)
        if divisor == 0:
            raise CalculationError("division_by_zero")
        value = left / divisor * 100
    elif operation_type == "difference":
        value = left - require_right(right)
    elif operation_type == "ratio":
        divisor = require_right(right)
        if divisor == 0:
            raise CalculationError("division_by_zero")
        value = left / divisor
    else:
        raise CalculationError("operation_type_not_supported")

    normalized_value = normalize_value(value)
    return CalculationResult(
        kind="operation_result",
        rows=[{"value": normalized_value}],
        row_count=1,
        metrics=["value"],
        columns=["value"],
        operation=operation,
    )


def require_right(value: int | float | None) -> int | float:
    if value is None:
        raise CalculationError("operation_operand_missing")
    return value


def calculate_query(
    db: Session,
    query_frame: QueryFrame,
    sql_query: SQLQuery | None,
    last_result: dict[str, Any] | None,
) -> CalculationResult:
    if query_frame.operation:
        return calculate_operation(query_frame.operation, last_result)
    if sql_query is None:
        raise CalculationError("sql_query_missing")
    return execute_sql_query(db, sql_query)
