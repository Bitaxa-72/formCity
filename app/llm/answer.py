import json

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import Settings
from app.llm.chat_options import build_chat_completion_options
from app.pipeline.response_data import ResponseData


ANSWER_SYSTEM_PROMPT = """
Ты оформляешь проверенные данные backend в короткий русский ответ.
Используй только числа, метрики, таблицы и source из входного JSON.
Не добавляй новые цифры.
Не делай новые расчеты.
Не упоминай SQL, JSON, backend и внутренние этапы.
Верни только валидный JSON.
"""

GENERAL_ANSWER_SYSTEM_PROMPT = """
Ты отвечаешь пользователю коротко по-русски.
Это общий вопрос или приветствие, не запрос к данным.
Не рассчитывай данные.
Не придумывай цифры.
Не упоминай SQL, JSON, backend и внутренние этапы.
Если пользователь здоровается, поздоровайся и кратко скажи, что можешь помочь с отчетами и данными проекта.
Верни только валидный JSON.
"""


class LLMAnswerError(RuntimeError):
    pass


class AnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    used_metrics: list[str] = Field(default_factory=list)
    source: dict[str, object] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


GENERAL_FALLBACK_TEXT = (
    "Не понял запрос к данным.\n\n"
    "Укажите, пожалуйста, тип отчета, проект, метрику и период.\n\n"
    "Доступные отчеты:\n"
    "- сводный отчет\n"
    "- модель\n"
    "- платежный календарь\n"
    "- дорожная карта\n"
    "- отчет о продажах\n"
    "- отчет об исполнении плана продаж\n"
    "- отчет по агентам\n"
    "- остатки в продаже\n"
    "- ДЗ и брони\n"
    "- непроектные расходы"
)
CAPABILITIES_TEXT = (
    "Я помогаю получать данные из подключенных отчетов.\n\n"
    "Сейчас подключены:\n\n"
    "Платежный календарь:\n"
    "- проекты: Московский, Обводный;\n"
    "- периоды: февраль 2026, март 2026, апрель 2026, май 2026;\n"
    "- показатели: план, факт, отклонение;\n"
    "- можно смотреть итоги, поступления, платежи, остатки и статьи расходов.\n\n"
    "Дорожная карта:\n"
    "- периоды: февраль 2026, март 2026, апрель 2026;\n"
    "- можно смотреть этапы, сроки этапов, итоговый срок и внешние этапы.\n\n"
    "Если проект не указан, покажу данные по всем проектам отдельно.\n"
    "Если период не указан для платежного календаря, возьму весь доступный период.\n"
    "Если период не указан для дорожной карты, возьму последний актуальный месяц."
)
ROADMAP_UNCLEAR_TEXT = (
    "Не понял запрос по дорожной карте.\n\n"
    "Укажите, что показать:\n"
    "- этапы\n"
    "- сроки этапов\n"
    "- итоговый срок\n"
    "- внешние этапы: банк или Росреестр\n"
    "- доступные периоды"
)

METRIC_LABELS = {
    "plan": "План",
    "fact": "Факт",
    "deviation": "Отклонение",
    "value": "Значение",
    "duration_min": "Минимальный срок",
    "duration_max": "Максимальный срок",
    "duration_range": "Диапазон срока",
    "step_count": "Количество этапов",
    "model_revenue": "\u0412\u044b\u0440\u0443\u0447\u043a\u0430",
    "model_cost_of_sales": "\u0421\u0435\u0431\u0435\u0441\u0442\u043e\u0438\u043c\u043e\u0441\u0442\u044c \u043f\u0440\u043e\u0434\u0430\u0436",
    "model_gross_profit": "\u0412\u0430\u043b\u043e\u0432\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c",
    "model_net_profit": "\u0427\u0438\u0441\u0442\u0430\u044f \u043f\u0440\u0438\u0431\u044b\u043b\u044c",
    "model_npv": "NPV",
    "model_roe": "ROE",
    "model_llcr": "LLCR",
    "model_total_area": "\u041e\u0431\u0449\u0430\u044f \u043f\u043b\u043e\u0449\u0430\u0434\u044c",
    "model_units_count": "\u041a\u043e\u043b\u0438\u0447\u0435\u0441\u0442\u0432\u043e \u043f\u043e\u043c\u0435\u0449\u0435\u043d\u0438\u0439",
    "model_pir": "\u041f\u0418\u0420",
    "amount": "Сумма",
    "executed_amount": "Исполнено",
    "remaining_amount": "Остаток / прогноз",
}

DIMENSION_LABELS = {
    "project": "Проект",
    "article": "Статья",
    "article_kind": "Раздел",
    "month": "Месяц",
    "period": "Период",
    "period_month": "Месяц",
    "row_order": "Порядок",
    "step": "Этап",
    "snapshot_month": "\u0421\u0440\u0435\u0437\u044b \u043c\u043e\u0434\u0435\u043b\u0438",
    "metric": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u0438",
    "parent_step": "Родительский этап",
    "action": "Действие",
    "external": "Внешний этап",
    "total": "Итого",
    "snapshot_month": "\u0421\u0440\u0435\u0437 \u043c\u043e\u0434\u0435\u043b\u0438",
    "metric": "\u041f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b\u044c",
    "item_kind": "Тип",
    "fm_category": "Категория",
    "item_name": "Строка",
    "row_type": "Вид строки",
}

DIMENSION_LIST_LABELS = {
    "article": "Статьи",
    "article_kind": "Разделы",
    "project": "Проекты",
    "period_month": "Периоды",
    "period": "Периоды",
    "month": "Месяцы",
    "step": "Этапы",
    "snapshot_month": "Срезы модели",
    "metric": "Показатели",
    "item_kind": "Типы",
    "fm_category": "Категории",
    "item_name": "Строки",
    "row_type": "Виды строк",
}

PROJECT_LABELS = {
    "obvodny": "Обводный",
    "moskovsky": "Московский",
    "evgenievsky": "Евгеньевский",
    "all": "Все проекты",
}

REPORT_LABELS = {
    "model": "\u041c\u043e\u0434\u0435\u043b\u044c",
    "non_project_expenses": "Непроектные расходы",
    "payment_calendar": "Платежный календарь",
    "roadmap": "Дорожная карта",
}

ARTICLE_KIND_LABELS = {
    "balance_start": "Остаток на начало",
    "income_total": "Поступления",
    "payment_total": "Итого платежи",
    "balance_end": "Остаток на конец",
    "detail": "Статья расходов",
}

NON_PROJECT_EXPENSES_ITEM_KIND_LABELS = {
    "lost_income": "Недополученные доходы",
    "debt_receivable": "ДЗ",
    "non_project_expenses_total": "Итог непроектных расходов",
    "personal": "Личное",
    "admin_expenses": "АХР",
    "evgenievsky": "ЕВГ",
    "legal_entity": "Юрлица",
    "fit_out": "Отделочные работы",
    "commercial": "Коммерческие расходы",
    "furniture": "Мебелировка",
    "construction": "Строительные работы",
    "developer_maintenance": "Содержание застройщика",
    "object_maintenance": "Содержание объекта и техзаказчик",
    "finance": "Финансовые расходы",
    "pir": "ПИР",
    "other_income_expense": "Прочие доходы и расходы",
    "other": "Прочее",
}

ROW_TYPE_LABELS = {
    "detail": "Детальная строка",
    "summary": "Итоговая строка",
}

ARTICLE_KIND_ORDER = {
    "balance_start": 0,
    "income_total": 1,
    "payment_total": 2,
    "balance_end": 3,
    "detail": 4,
}

MISSING_METRIC_TEXT = {
    "plan": "план не заполнен",
    "fact": "факт не заполнен",
    "deviation": "отклонение не заполнено",
    "value": "значение не заполнено",
}

MONTH_LABELS = {
    "01": "январь",
    "02": "февраль",
    "03": "март",
    "04": "апрель",
    "05": "май",
    "06": "июнь",
    "07": "июль",
    "08": "август",
    "09": "сентябрь",
    "10": "октябрь",
    "11": "ноябрь",
    "12": "декабрь",
}


def format_number(value: object) -> str:
    if value is None:
        return "нет данных"
    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")
    if isinstance(value, float):
        formatted = f"{value:,.2f}".replace(",", " ")
        return formatted.rstrip("0").rstrip(".")
    return str(value)


def format_unit(unit: object) -> str:
    if unit in {"rub", "руб."}:
        return " руб."
    if unit == "work_day":
        return " раб. дн."
    if unit == "percent":
        return "%"
    if unit == "square_meter":
        return " м2"
    if unit == "count":
        return ""
    if unit == "ratio":
        return ""
    return f" {unit}" if unit else ""


def format_metric_line(metric: str, value: object, unit: object) -> str:
    suffix = "" if value is None else format_unit(unit)
    return f"{METRIC_LABELS.get(metric, metric)}: {format_number(value)}{suffix}"


def format_work_days(min_days: object, max_days: object) -> str:
    if min_days is None and max_days is None:
        return "нет данных"
    if min_days == max_days or max_days is None:
        return f"{format_number(min_days)} раб. дн."
    if min_days is None:
        return f"{format_number(max_days)} раб. дн."
    return f"{format_number(min_days)}-{format_number(max_days)} раб. дн."


def format_period(source: dict[str, object]) -> str:
    period = source.get("period")
    if not isinstance(period, dict):
        return "выбранный период"

    label = period.get("label")
    if isinstance(label, str) and label:
        from_date = period.get("from")
        if isinstance(from_date, str) and len(from_date) >= 4 and from_date[:4] not in label:
            return f"{label} {from_date[:4]}"
        return label

    from_date = period.get("from")
    to_date = period.get("to")
    if isinstance(from_date, str) and isinstance(to_date, str):
        if len(from_date) >= 7 and len(to_date) >= 7 and from_date[:7] == to_date[:7]:
            return f"{MONTH_LABELS.get(from_date[5:7], from_date[5:7])} {from_date[:4]}"
        return f"{from_date} - {to_date}"
    return "выбранный период"


def format_filter_subject(source: dict[str, object]) -> str:
    filters = source.get("filters")
    if not isinstance(filters, dict):
        return ""

    article = filters.get("article")
    if isinstance(article, str) and article:
        return f'По статье "{article}"'
    return ""


def build_answer_header(response_data: ResponseData) -> list[str]:
    source = response_data.source
    report_type = source.get("report_type")
    lines = [REPORT_LABELS.get(report_type, response_data.title)]

    table_rows = response_data.table.rows if response_data.table else []
    has_project_rows = any("project" in row for row in table_rows)
    project = source.get("project")
    if (
        isinstance(project, str)
        and project
        and not (project == "all" and has_project_rows)
        and not (project == "all" and source.get("report_type") == "non_project_expenses")
    ):
        lines.append(f"Проект: {PROJECT_LABELS.get(project, project)}")

    period = format_period(source)
    if period:
        lines.append(f"Период: {period}")

    filters = source.get("filters")
    if isinstance(filters, dict):
        article = filters.get("article")
        if isinstance(article, str) and article:
            lines.append(f"Статья: {article}")
        elif isinstance(article, list) and article:
            lines.append("Статьи: " + ", ".join(str(item) for item in article))
        elif "article_kind" in filters and not has_project_rows:
            article_kind = filters.get("article_kind")
            if isinstance(article_kind, str):
                lines.append(f"Раздел: {format_dimension_value('article_kind', article_kind)}")
            elif isinstance(article_kind, list) and len(article_kind) == 1:
                lines.append(f"Раздел: {format_dimension_value('article_kind', article_kind[0])}")

    return lines


def build_missing_value_answer(response_data: ResponseData, missing_metric: str) -> AnswerDraft:
    source = response_data.source
    period = format_period(source)
    subject = format_filter_subject(source) or "По заданным условиям"
    missing_text = MISSING_METRIC_TEXT.get(missing_metric, "значение не заполнено")
    lines = [f"{subject} за {period} {missing_text}."]

    row = response_data.table.rows[0] if response_data.table and response_data.table.rows else {}
    units = source.get("units") if isinstance(source.get("units"), dict) else {}
    for metric in ["plan", "fact", "deviation"]:
        if metric not in row:
            continue
        value = row.get(metric)
        raw_unit = units.get(metric) if isinstance(units, dict) else None
        if raw_unit is None and source.get("report_type") in {"payment_calendar", "model", "non_project_expenses"}:
            raw_unit = "rub"
        lines.append(format_metric_line(metric, value, raw_unit))

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=list(source.get("metrics") or []),
        source=source,
        warnings=response_data.warnings,
    )


def is_truthy(value: object) -> bool:
    return value is True or value == 1 or value == "1"


def build_roadmap_answer(response_data: ResponseData) -> AnswerDraft | None:
    if response_data.source.get("report_type") != "roadmap":
        return None
    if response_data.source.get("intent") == "dimension_query":
        return None
    if response_data.table is None or not response_data.table.rows:
        return None

    rows = sorted(
        response_data.table.rows,
        key=lambda row: (
            int(row.get("row_order") or 0),
            int(row.get("step") or 0),
        ),
    )
    lines = ["Дорожная карта", f"Период: {format_period(response_data.source)}", ""]

    view = response_data.source.get("view")
    filters = response_data.source.get("filters")
    if view == "step_count":
        row = rows[0]
        lines.append(f"Основных этапов: {format_number(row.get('step_count'))}")
        return AnswerDraft(
            text="\n".join(lines),
            used_metrics=list(response_data.source.get("metrics") or []),
            source=response_data.source,
            warnings=response_data.warnings,
        )

    if view == "total_duration" or (isinstance(filters, dict) and filters.get("is_total") is True):
        row = rows[0]
        lines.append(f"Итого: {format_work_days(row.get('duration_min'), row.get('duration_max'))}")
        return AnswerDraft(
            text="\n".join(lines),
            used_metrics=list(response_data.source.get("metrics") or []),
            source=response_data.source,
            warnings=response_data.warnings,
        )

    for row in rows:
        action = row.get("action")
        if not isinstance(action, str) or not action.strip():
            continue

        if is_truthy(row.get("total")):
            lines.append(f"Итого: {format_work_days(row.get('duration_min'), row.get('duration_max'))}")
            continue

        step = row.get("step")
        prefix = f"{int(step)}. " if isinstance(step, int | float) and step else "- "
        lines.append(prefix + action.strip())
        if row.get("duration_min") is not None or row.get("duration_max") is not None:
            lines.append(f"Срок: {format_work_days(row.get('duration_min'), row.get('duration_max'))}")
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()
    if response_data.table.truncated:
        lines.append("")
        lines.append(f"Показаны первые {len(response_data.table.rows)} из {response_data.table.total_rows} строк.")

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=list(response_data.source.get("metrics") or []),
        source=response_data.source,
        warnings=response_data.warnings,
    )


def build_ready_answer(response_data: ResponseData) -> AnswerDraft:
    roadmap_answer = build_roadmap_answer(response_data)
    if roadmap_answer is not None:
        return roadmap_answer

    table_answer = build_table_answer(response_data)
    if table_answer is not None:
        return table_answer

    lines = build_answer_header(response_data)
    lines.append("")
    if response_data.summary:
        for item in response_data.summary:
            lines.append(f"{item.label}: {format_number(item.value)}{format_unit(item.unit)}")
    elif response_data.table and response_data.table.rows:
        row = response_data.table.rows[0]
        units = response_data.source.get("units") if isinstance(response_data.source.get("units"), dict) else {}
        metric_names = [metric for metric in response_data.source.get("metrics", []) if isinstance(metric, str)]
        for metric in metric_names:
            if metric not in row:
                continue
            raw_unit = units.get(metric) if isinstance(units, dict) else None
            if raw_unit is None and response_data.source.get("report_type") in {"payment_calendar", "model", "non_project_expenses"}:
                raw_unit = "rub"
            value = row.get(metric)
            lines.append(format_metric_line(metric, value, raw_unit))

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=[item.metric for item in response_data.summary],
        source=response_data.source,
        warnings=response_data.warnings,
    )


def format_dimension_value(key: str, value: object) -> str:
    if key == "project" and isinstance(value, str):
        return PROJECT_LABELS.get(value, value)
    if key == "article_kind" and isinstance(value, str):
        return ARTICLE_KIND_LABELS.get(value, value)
    if key == "item_kind" and isinstance(value, str):
        return NON_PROJECT_EXPENSES_ITEM_KIND_LABELS.get(value, value)
    if key == "row_type" and isinstance(value, str):
        return ROW_TYPE_LABELS.get(value, value)
    if key == "metric" and isinstance(value, str):
        return METRIC_LABELS.get(value, value)
    if key in {"period", "period_month", "month"} and isinstance(value, str) and len(value) >= 7:
        month = MONTH_LABELS.get(value[5:7])
        year = value[:4]
        if month and year.isdigit():
            return f"{month} {year}"
    if key == "snapshot_month" and isinstance(value, str) and len(value) >= 7:
        month = MONTH_LABELS.get(value[5:7])
        year = value[:4]
        if month and year.isdigit():
            return f"{month} {year}"
    return str(value)


def build_dimension_answer(response_data: ResponseData) -> AnswerDraft | None:
    table = response_data.table
    if table is None or not table.rows:
        return None
    if not table.columns:
        return None
    if response_data.source.get("intent") != "dimension_query" and response_data.source.get("metrics"):
        return None

    dimension = response_data.source.get("dimension")
    column = dimension if isinstance(dimension, str) and dimension in table.columns else table.columns[0]
    values = [format_dimension_value(column, row.get(column)) for row in table.rows if row.get(column) is not None]
    if not values:
        return None

    lines = build_answer_header(response_data)
    lines.append("")
    lines.append(f"{DIMENSION_LIST_LABELS.get(column, DIMENSION_LABELS.get(column, column))}:")
    lines.extend(f"- {value}" for value in values)
    if table.truncated:
        lines.append(f"Показаны первые {len(values)} из {table.total_rows} значений.")

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=[],
        source=response_data.source,
        warnings=response_data.warnings,
    )


def build_row_title(row: dict[str, object], metric_names: list[str]) -> str:
    if "project" in row and "article_kind" in row:
        return f"Проект: {format_dimension_value('project', row['project'])}, {format_dimension_value('article_kind', row['article_kind'])}"
    if "article_kind" in row:
        return format_dimension_value("article_kind", row["article_kind"])

    dimension_parts = []
    for key, value in row.items():
        if key in metric_names or key in {"plan", "fact", "deviation", "value"}:
            continue
        if value is None:
            continue
        label = DIMENSION_LABELS.get(key, key)
        dimension_parts.append(f"{label}: {format_dimension_value(key, value)}")
    return ", ".join(dimension_parts) if dimension_parts else "Итого"


def sort_payment_calendar_rows(response_data: ResponseData) -> list[dict[str, object]]:
    table = response_data.table
    if table is None:
        return []
    if response_data.source.get("report_type") != "payment_calendar":
        return table.rows
    return sorted(
        table.rows,
        key=lambda row: (
            str(row.get("project") or ""),
            ARTICLE_KIND_ORDER.get(str(row.get("article_kind") or ""), 100),
            str(row.get("article") or ""),
        ),
    )


def build_table_answer(response_data: ResponseData) -> AnswerDraft | None:
    dimension_answer = build_dimension_answer(response_data)
    if dimension_answer is not None:
        return dimension_answer

    table = response_data.table
    if table is None or not table.rows:
        return None

    metric_names = [metric for metric in response_data.source.get("metrics", []) if isinstance(metric, str)]
    if not metric_names:
        metric_names = [item.metric for item in response_data.summary]
    if not metric_names:
        return None

    has_dimensions = any(
        key not in set(metric_names) | {"plan", "fact", "deviation", "value"}
        for row in table.rows
        for key in row
    )
    if not has_dimensions and table.total_rows <= 1:
        return None

    units = response_data.source.get("units") if isinstance(response_data.source.get("units"), dict) else {}
    lines = build_answer_header(response_data)
    for row in sort_payment_calendar_rows(response_data):
        lines.append("")
        lines.append(f"{build_row_title(row, metric_names)}:")
        for metric in metric_names:
            if metric not in row:
                continue
            raw_unit = units.get(metric) if isinstance(units, dict) else None
            if raw_unit is None and response_data.source.get("report_type") in {"payment_calendar", "model", "non_project_expenses"}:
                raw_unit = "rub"
            value = row.get(metric)
            lines.append(format_metric_line(metric, value, raw_unit))

    if table.truncated:
        lines.append("")
        lines.append(f"Показаны первые {len(table.rows)} из {table.total_rows} строк.")

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=metric_names,
        source=response_data.source,
        warnings=response_data.warnings,
    )


def build_unready_answer(response_data: ResponseData | None) -> AnswerDraft:
    errors = response_data.errors if response_data else ["response_data_missing"]
    text = "По заданным условиям данных не найдено." if response_data and "empty_result" in errors else "Не удалось подготовить проверенный ответ по данным."
    return AnswerDraft(
        text=text,
        used_metrics=[],
        source=response_data.source if response_data else {},
        warnings=errors,
    )


def build_fallback_answer(response_data: ResponseData | None) -> AnswerDraft:
    if response_data is None or not response_data.ready:
        return build_unready_answer(response_data)

    roadmap_answer = build_roadmap_answer(response_data)
    if roadmap_answer is not None:
        return roadmap_answer

    missing_metrics = response_data.source.get("missing_metrics")
    requested_metrics = response_data.source.get("metrics")
    if isinstance(missing_metrics, list) and missing_metrics and isinstance(requested_metrics, list) and len(requested_metrics) == 1:
        metric = next((item for item in missing_metrics if isinstance(item, str)), None)
        if metric:
            return build_missing_value_answer(response_data, metric)

    return build_ready_answer(response_data)


def normalize_answer_payload(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError("answer payload must be an object")

    normalized = dict(payload)
    if "text" not in normalized:
        for key in ("answer", "message", "response"):
            value = normalized.get(key)
            if isinstance(value, str) and value.strip():
                normalized["text"] = value
                break

    return {
        "text": normalized.get("text"),
        "used_metrics": normalized.get("used_metrics", []),
        "source": normalized.get("source", {}),
        "warnings": normalized.get("warnings", []),
    }


def validate_answer_payload(payload: object, error_message: str) -> AnswerDraft:
    try:
        return AnswerDraft.model_validate(normalize_answer_payload(payload))
    except (ValueError, ValidationError) as error:
        raise LLMAnswerError(error_message) from error


def build_general_fallback_answer() -> AnswerDraft:
    return AnswerDraft(text=GENERAL_FALLBACK_TEXT)


def build_roadmap_unclear_answer() -> AnswerDraft:
    return AnswerDraft(text=ROADMAP_UNCLEAR_TEXT)


def build_capabilities_answer() -> AnswerDraft:
    return AnswerDraft(text=CAPABILITIES_TEXT)


class OpenAILLMAnswerer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build_answer(self, response_data: ResponseData | None) -> AnswerDraft:
        if response_data is None or not response_data.ready:
            return build_unready_answer(response_data)
        if response_data.source.get("report_type") in {"payment_calendar", "roadmap", "model", "non_project_expenses"}:
            return build_fallback_answer(response_data)
        table_answer = build_table_answer(response_data)
        if table_answer is not None:
            return table_answer
        if not self.settings.openai_key:
            raise LLMAnswerError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMAnswerError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": response_data.model_dump_json()},
                ],
                **build_chat_completion_options(self.settings.openai_model),
            )

        content = response.choices[0].message.content
        if not content:
            raise LLMAnswerError("LLM returned empty answer")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMAnswerError("LLM returned invalid answer JSON") from error

        return validate_answer_payload(payload, "LLM returned invalid answer schema")

    async def build_general_answer(self, user_message: str | None) -> AnswerDraft:
        if not self.settings.openai_key:
            raise LLMAnswerError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMAnswerError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": GENERAL_ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message or ""},
                ],
                **build_chat_completion_options(self.settings.openai_model),
            )

        content = response.choices[0].message.content
        if not content:
            raise LLMAnswerError("LLM returned empty general answer")

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMAnswerError("LLM returned invalid general answer JSON") from error

        return validate_answer_payload(payload, "LLM returned invalid general answer schema")
