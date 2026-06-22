from typing import Any

from pydantic import BaseModel

from app.calculation_engine import CalculationResult
from app.result_verifier import ResultVerification


MAX_TABLE_ROWS = 10

METRIC_LABELS = {
    "revenue": "Выручка",
    "sold_area": "Проданная площадь",
    "deal_count": "Количество сделок",
    "average_deal_price": "Средняя цена сделки",
    "price_per_square_meter": "Цена за квадратный метр",
    "debt": "Задолженность",
    "booking_amount": "Сумма брони",
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "agent_commission": "Агентское вознаграждение",
    "pledge_release_amount": "Сумма вывода из залога",
    "remaining_amount": "Остаток",
    "value": "Значение",
}

UNIT_LABELS = {
    "rub": "руб.",
    "square_meter": "м2",
    "count": "шт.",
    "rub_per_square_meter": "руб./м2",
}


class ResponseSummaryItem(BaseModel):
    metric: str
    label: str
    value: Any
    unit: str | None = None


class ResponseTable(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    total_rows: int
    truncated: bool


class ResponseData(BaseModel):
    ready: bool
    title: str
    summary: list[ResponseSummaryItem]
    table: ResponseTable | None
    source: dict[str, Any]
    warnings: list[str]
    errors: list[str]


def build_title(source: dict[str, Any], metrics: list[str]) -> str:
    report_type = source.get("report_type") or "unknown"
    project = source.get("project") or "all"
    metric_labels = ", ".join(METRIC_LABELS.get(metric, metric) for metric in metrics)
    if metric_labels:
        return f"{metric_labels}: {report_type}, {project}"
    return f"{report_type}, {project}"


def build_summary(
    calculation_result: CalculationResult,
    verification: ResultVerification,
) -> list[ResponseSummaryItem]:
    if not calculation_result.rows:
        return []

    units = verification.source.get("units") or {}
    first_row = calculation_result.rows[0]
    summary = []

    for metric in calculation_result.metrics:
        if metric not in first_row:
            continue
        unit = units.get(metric)
        summary.append(
            ResponseSummaryItem(
                metric=metric,
                label=METRIC_LABELS.get(metric, metric),
                value=first_row[metric],
                unit=UNIT_LABELS.get(unit, unit),
            ),
        )

    return summary


def build_table(calculation_result: CalculationResult) -> ResponseTable | None:
    if not calculation_result.rows or not calculation_result.columns:
        return None

    rows = calculation_result.rows[:MAX_TABLE_ROWS]
    return ResponseTable(
        columns=calculation_result.columns,
        rows=rows,
        total_rows=calculation_result.row_count,
        truncated=calculation_result.row_count > len(rows),
    )


def build_response_data(
    calculation_result: CalculationResult | None,
    verification: ResultVerification | None,
) -> ResponseData:
    if verification is None:
        return ResponseData(
            ready=False,
            title="Результат не проверен",
            summary=[],
            table=None,
            source={},
            warnings=[],
            errors=["verification_missing"],
        )

    if calculation_result is None:
        return ResponseData(
            ready=False,
            title="Результат отсутствует",
            summary=[],
            table=None,
            source=verification.source,
            warnings=verification.warnings,
            errors=verification.errors or ["result_missing"],
        )

    summary = build_summary(calculation_result, verification)
    table = build_table(calculation_result)

    return ResponseData(
        ready=verification.verified,
        title=build_title(verification.source, calculation_result.metrics),
        summary=summary,
        table=table,
        source=verification.source,
        warnings=verification.warnings,
        errors=verification.errors,
    )
