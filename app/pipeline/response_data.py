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
    "stock_ddu_amount": "Сумма ДДУ",
    "stock_dupt_markup_amount": "Наценка ДУПТ",
    "stock_total_amount": "Сумма всего",
    "stock_area_sqm": "Площадь",
    "stock_unit_count": "Количество объектов",
    "stock_ddu_price_per_sqm": "Цена ДДУ за м2",
    "stock_dupt_price_per_sqm": "Цена ДУПТ за м2",
    "stock_total_price_per_sqm": "Цена за м2",
    "sales_contract_revenue": "Выручка по контрактации",
    "sales_contract_area_sqm": "Объем контрактации",
    "sales_contract_count": "Количество сделок",
    "sales_price_per_sqm": "Цена за м2",
    "sales_ddu_actual_payments": "Фактические оплаты по ДДУ",
    "sales_ddu_remaining_payment_schedule": "График оплаты остатка по ДДУ",
    "sales_cumulative_price_per_sqm": "Накопительная цена за м2",
    "sales_plan_revenue": "Продажи",
    "sales_plan_cash_receipts": "Поступления денежных средств",
    "sales_plan_contract_area_sqm": "Площадь контрактации",
    "sales_plan_contract_count": "Количество сделок",
    "sales_plan_price_per_sqm": "Цена за м2",
    "agents_deal_count": "Количество сделок",
    "agents_area_sqm": "Площадь",
    "agents_commission_base_amount": "База вознаграждения",
    "agents_commission_amount": "Агентское вознаграждение",
    "agents_act_total_amount": "Сумма по акту",
    "agents_paid_amount": "Оплачено",
    "agents_remaining_amount": "Остаток к оплате",
    "agents_ddu_assignment_amount": "ДДУ + уступка",
    "agents_ddu_amount": "ДДУ",
    "agents_assignment_amount": "Уступка",
    "agents_furniture_amount": "Меблировка",
    "agents_monthly_value": "Сумма графика",
    "summary_sheet_count": "Количество листов",
    "summary_row_count": "Количество строк",
    "summary_cell_count": "Количество ячеек",
    "summary_numeric_cell_count": "Числовые ячейки",
    "summary_value_sum": "Сумма значений",
    "unit_number": "Номер помещения",
    "agent": "Агент",
}

UNIT_LABELS = {
    "rub": "руб.",
    "percent": "%",
    "ratio": "",
    "square_meter": "м2",
    "count": "",
    "rub_per_square_meter": "руб./м2",
    "sqm": "м2",
    "thousand_rub": "тыс. руб.",
    "thousand_rub_per_sqm": "тыс. руб./м2",
    "thousand_rub_per_square_meter": "тыс. руб./м2",
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
