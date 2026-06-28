from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.pipeline.calculation_engine import CalculationResult
from app.pipeline.result_verifier import ResultVerification
from app.pipeline.sensitive_data import is_public_text_column, sanitize_value, visible_columns as sanitized_visible_columns, visible_rows


PDF_REPORT_THRESHOLD = 30
PDF_REPORT_NOTICE = "Отчет слишком большой, оформлю вам PDF."
PDF_FONT_NAME = "FormCitySans"
REPORT_LABELS = {
    "model": "Модель",
    "payment_calendar": "Платежный календарь",
    "roadmap": "Дорожная карта",
}
PROJECT_LABELS = {
    "obvodny": "Обводный",
    "moskovsky": "Московский",
    "evgenievsky": "Евгеньевский",
    "all": "Все проекты",
}
COLUMN_LABELS = {
    "project": "Проект",
    "period": "Период",
    "period_month": "Период",
    "month": "Месяц",
    "article": "Статья",
    "article_kind": "Тип строки",
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "value": "Значение",
    "row_order": "Порядок",
    "step": "Этап",
    "parent_step": "Родительский этап",
    "action": "Действие",
    "external": "Внешний этап",
    "total": "Итого",
    "duration_min": "Минимальный срок",
    "duration_max": "Максимальный срок",
    "duration_range": "Диапазон срока",
    "step_count": "Количество этапов",
    "snapshot_month": "Срез модели",
    "metric": "Показатель",
    "metric_name": "Показатель",
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
    "raw_sheet": "Лист",
    "row_count": "Строк",
    "cell_count": "Ячеек",
    "row_number": "Номер строки",
    "row_label": "Название строки",
    "visible_cells": "Открытых ячеек",
    "values_preview": "Значения",
}
ARTICLE_KIND_LABELS = {
    "balance_start": "Остаток на начало",
    "income_total": "Поступления",
    "payment_total": "Итого платежи",
    "balance_end": "Остаток на конец",
    "detail": "Статья расходов",
}
RAW_SHEET_LABELS = {
    "consolidation": "Для консолидации",
    "для консолидации": "Для консолидации",
    "консолидация": "Для консолидации",
    "financial_model": "Финмодель",
    "финмодель": "Финмодель",
    "фин модель": "Финмодель",
    "финансовая модель": "Финмодель",
    "remains": "Остатки",
    "остатки": "Остатки",
    "остаток": "Остатки",
}
MONEY_COLUMNS = {
    "plan",
    "fact",
    "deviation",
    "value",
    "model_revenue",
    "model_cost_of_sales",
    "model_gross_profit",
    "model_net_profit",
    "model_npv",
    "model_pir",
}


def find_pdf_font() -> str | None:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/Calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def register_pdf_font() -> str:
    font_path = find_pdf_font()
    if not font_path:
        return "Helvetica"
    if PDF_FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, font_path))
    return PDF_FONT_NAME


def should_send_pdf_report(calculation_result: CalculationResult | None) -> bool:
    return bool(calculation_result and calculation_result.kind == "sql_result" and calculation_result.row_count > PDF_REPORT_THRESHOLD)


def format_number(value: int | float) -> str:
    if isinstance(value, float):
        formatted = f"{value:,.2f}".replace(",", " ")
        return formatted.rstrip("0").rstrip(".")
    return f"{value:,}".replace(",", " ")


def format_value(column: str, value: Any) -> str:
    value = value if is_public_text_column(column) else sanitize_value(value)
    if value is None:
        return ""
    if column == "project" and isinstance(value, str):
        return PROJECT_LABELS.get(value, value)
    if column == "article_kind" and isinstance(value, str):
        return ARTICLE_KIND_LABELS.get(value, value)
    if column == "raw_sheet" and isinstance(value, str):
        normalized = " ".join(value.strip().lower().replace("ё", "е").split())
        return RAW_SHEET_LABELS.get(normalized, value)
    if column in MONEY_COLUMNS and isinstance(value, int | float):
        return f"{format_number(value)} руб."
    if isinstance(value, int | float):
        return format_number(value)
    return str(value)


def build_report_title_lines(source: dict[str, Any]) -> list[str]:
    report_type = source.get("report_type") or "report"
    project = source.get("project") or "all"
    period = source.get("period") or {}
    period_label = period.get("label") or "весь доступный период"
    lines = [REPORT_LABELS.get(report_type, str(report_type))]
    lines.append(f"Период: {period_label}")
    if isinstance(project, str):
        lines.append(f"Проект: {PROJECT_LABELS.get(project, project)}")
    filters = source.get("filters")
    if isinstance(filters, dict):
        article = filters.get("article")
        if isinstance(article, str) and article:
            lines.append(f"Статья: {article}")
        raw_sheet = filters.get("raw_sheet")
        if isinstance(raw_sheet, str) and raw_sheet:
            lines.append(f"Лист: {format_value('raw_sheet', raw_sheet)}")
        raw_query = filters.get("raw_query")
        if isinstance(raw_query, str) and raw_query:
            lines.append(f"Поиск: {raw_query}")
    return lines


def visible_columns(columns: list[str]) -> list[str]:
    return sanitized_visible_columns(columns)


def column_label(column: str) -> str:
    return COLUMN_LABELS.get(column, column)


def build_pdf_report(
    calculation_result: CalculationResult,
    verification: ResultVerification,
) -> tuple[bytes, str]:
    font_name = register_pdf_font()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=20,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=9,
        leading=11,
    )

    elements = [Paragraph(build_report_title_lines(verification.source)[0], title_style)]
    for line in build_report_title_lines(verification.source)[1:]:
        elements.append(Paragraph(line, body_style))
    elements.extend([Paragraph(f"Строк: {calculation_result.row_count}", body_style), Spacer(1, 12)])

    columns = visible_columns(calculation_result.columns)
    rows = visible_rows(calculation_result.rows)
    data = [[Paragraph(column_label(column), body_style) for column in columns]]
    for row in rows:
        data.append([Paragraph(format_value(column, row.get(column)), body_style) for column in columns])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ],
        ),
    )
    elements.append(table)
    document.build(elements)
    filename = f"{verification.source.get('report_type') or 'report'}.pdf"
    return buffer.getvalue(), filename
