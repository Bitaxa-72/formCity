from typing import Any

from pydantic import BaseModel

from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.result_verifier import ResultVerification
from app.pipeline.sensitive_data import visible_columns, visible_rows


MAX_TABLE_ROWS = 10
MAX_ROADMAP_TABLE_ROWS = 50

METRIC_LABELS = {
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "value": "Значение",
    "model_revenue": "Выручка",
    "model_cost_of_sales": "Себестоимость продаж",
    "model_gross_profit": "Валовая прибыль",
    "model_net_profit": "Чистая прибыль",
    "model_npv": "NPV",
    "model_roe": "ROE",
    "model_llcr": "LLCR",
    "model_total_area": "Общая площадь",
    "model_units_count": "Количество помещений",
    "model_pir": "ПИР",
    "amount": "Сумма",
    "executed_amount": "Исполнено",
    "remaining_amount": "Остаток / прогноз",
}

UNIT_LABELS = {
    "rub": "руб.",
    "percent": "%",
    "ratio": "",
    "square_meter": "м2",
    "count": "",
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
        summary.append(
            ResponseSummaryItem(
                metric=metric,
                label=METRIC_LABELS.get(metric, metric),
                value=first_row[metric],
                unit=UNIT_LABELS.get(units.get(metric), units.get(metric)),
            ),
        )
    return summary


def build_table(calculation_result: CalculationResult, max_rows: int = MAX_TABLE_ROWS) -> ResponseTable:
    rows = visible_rows(calculation_result.rows)
    return ResponseTable(
        columns=visible_columns(calculation_result.columns),
        rows=rows[:max_rows],
        total_rows=len(rows),
        truncated=len(rows) > max_rows,
    )


def build_response_data(
    calculation_result: CalculationResult | None,
    verification: ResultVerification | None,
) -> ResponseData:
    if verification is None:
        return ResponseData(
            ready=False,
            title="Результат отсутствует",
            summary=[],
            table=None,
            source={},
            warnings=[],
            errors=["verification_missing"],
        )

    if calculation_result is None or not verification.verified:
        return ResponseData(
            ready=False,
            title="Результат отсутствует",
            summary=[],
            table=None,
            source=verification.source,
            warnings=verification.warnings,
            errors=verification.errors,
        )

    return ResponseData(
        ready=True,
        title=build_title(verification.source, calculation_result.metrics),
        summary=build_summary(calculation_result, verification),
        table=build_table(
            calculation_result,
            MAX_ROADMAP_TABLE_ROWS if verification.source.get("report_type") == "roadmap" else MAX_TABLE_ROWS,
        ),
        source=verification.source,
        warnings=verification.warnings,
        errors=verification.errors,
    )
