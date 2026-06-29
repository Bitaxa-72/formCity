from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
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
    "model_pir_total": "ПИР",
    "model_pir_per_sqm": "ПИР на м2",
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
    "model_pir_total",
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
    if column == "model_pir_per_sqm" and isinstance(value, int | float):
        return f"{format_number(value)} руб./м2"
    if isinstance(value, int | float):
        return format_number(value)
    return str(value)


def format_pdf_text(column: str, value: Any) -> str:
    text = format_value(column, value)
    if column == "values_preview":
        text = text.replace(" | ", "<br/>")
    return text


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


def excel_column_index(column: str) -> int:
    result = 0
    for char in column.upper():
        if not ("A" <= char <= "Z"):
            return 10_000
        result = result * 26 + ord(char) - ord("A") + 1
    return result


def split_long_token(value: str, chunk_size: int = 36) -> str:
    parts = []
    for token in value.split(" "):
        if len(token) <= chunk_size:
            parts.append(token)
            continue
        parts.extend(token[index:index + chunk_size] for index in range(0, len(token), chunk_size))
    return " ".join(parts)


def parse_values_preview(value: object) -> dict[str, str]:
    if not isinstance(value, str):
        return {}
    result = {}
    for item in value.split(" | "):
        if ": " not in item:
            continue
        column, cell_value = item.split(": ", 1)
        column = column.strip()
        if column:
            result[column] = split_long_token(cell_value.strip())
    return result


def chunked(items: list[str], size: int) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def build_model_raw_rows_pdf_elements(
    calculation_result: CalculationResult,
    verification: ResultVerification,
    title_style: ParagraphStyle,
    body_style: ParagraphStyle,
) -> list[Any]:
    elements = [Paragraph(build_report_title_lines(verification.source)[0], title_style)]
    for line in build_report_title_lines(verification.source)[1:]:
        elements.append(Paragraph(line, body_style))
    elements.extend([Paragraph(f"Строк: {calculation_result.row_count}", body_style), Spacer(1, 12)])

    rows = visible_rows(calculation_result.rows)
    parsed_rows = [(row, parse_values_preview(row.get("values_preview"))) for row in rows]
    value_columns = sorted(
        {column for _, values in parsed_rows for column in values},
        key=excel_column_index,
    )
    if not value_columns:
        value_columns = ["values_preview"]

    raw_table_style = ParagraphStyle(
        "RawTableBody",
        parent=body_style,
        fontSize=7,
        leading=8,
    )
    for chunk_index, value_chunk in enumerate(chunked(value_columns, 6)):
        if chunk_index:
            elements.append(PageBreak())
        chunk_label = f"Колонки {value_chunk[0]}-{value_chunk[-1]}" if value_chunk else "Значения"
        elements.append(Paragraph(chunk_label, body_style))
        elements.append(Spacer(1, 6))

        data = [
            [Paragraph("Строка", raw_table_style), Paragraph("Название", raw_table_style)]
            + [Paragraph(column, raw_table_style) for column in value_chunk],
        ]
        for row, values in parsed_rows:
            row_number = row.get("row_number")
            row_label = row.get("row_label") or ""
            data.append(
                [
                    Paragraph(format_number(row_number) if isinstance(row_number, int | float) else "", raw_table_style),
                    Paragraph(split_long_token(str(row_label)), raw_table_style),
                ]
                + [Paragraph(values.get(column, ""), raw_table_style) for column in value_chunk],
            )

        available_width = landscape(A4)[0] - 48
        first_width = 34
        label_width = 130
        value_width = (available_width - first_width - label_width) / max(len(value_chunk), 1)
        table = Table(
            data,
            colWidths=[first_width, label_width] + [value_width] * len(value_chunk),
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), body_style.fontName),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ],
            ),
        )
        elements.append(table)
    return elements


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

    if verification.source.get("report_type") == "model" and verification.source.get("view") in {"model_raw_rows", "model_raw_search"}:
        elements = build_model_raw_rows_pdf_elements(calculation_result, verification, title_style, body_style)
        document.build(elements)
        filename = f"{verification.source.get('report_type') or 'report'}.pdf"
        return buffer.getvalue(), filename

    elements = [Paragraph(build_report_title_lines(verification.source)[0], title_style)]
    for line in build_report_title_lines(verification.source)[1:]:
        elements.append(Paragraph(line, body_style))
    elements.extend([Paragraph(f"Строк: {calculation_result.row_count}", body_style), Spacer(1, 12)])

    columns = visible_columns(calculation_result.columns)
    rows = visible_rows(calculation_result.rows)
    data = [[Paragraph(column_label(column), body_style) for column in columns]]
    for row in rows:
        data.append([Paragraph(format_pdf_text(column, row.get(column)), body_style) for column in columns])

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
