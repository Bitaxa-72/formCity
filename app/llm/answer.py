from app.llm.answer_labels import *


TEMPLATE_REPORT_TYPES = {
    "payment_calendar",
    "roadmap",
    "model",
    "non_project_expenses",
    "debt_and_bookings",
    "stock_for_sale",
    "sales_report",
    "sales_plan_execution",
    "agents_report",
    "summary",
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
    if unit == "thousand_rub":
        return " тыс. руб."
    if unit == "thousand_rub_per_square_meter":
        return " тыс. руб./м2"
    if unit == "work_day":
        return " раб. дн."
    if unit == "percent":
        return "%"
    if unit in {"square_meter", "sqm"}:
        return " м2"
    if unit in {"rub_per_square_meter", "rub_per_sqm"}:
        return " руб./м2"
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

    notices = source.get("notices")
    if isinstance(notices, list):
        lines.extend(str(notice) for notice in notices if isinstance(notice, str) and notice)

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
        if raw_unit is None and source.get("report_type") in {"payment_calendar", "model", "non_project_expenses", "debt_and_bookings", "stock_for_sale", "sales_report"}:
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


def build_model_raw_answer(response_data: ResponseData) -> AnswerDraft | None:
    if response_data.source.get("report_type") != "model":
        return None
    view = response_data.source.get("view")
    if view not in {"model_raw_sheets", "model_raw_rows", "model_raw_search"}:
        return None
    if response_data.table is None or not response_data.table.rows:
        return None

    lines = build_answer_header(response_data)
    lines.append("")

    if view == "model_raw_sheets":
        lines.append("Листы модели:")
        for row in response_data.table.rows:
            sheet = row.get("raw_sheet")
            if sheet is None:
                continue
            row_count = row.get("row_count")
            cell_count = row.get("cell_count")
            details = []
            if row_count is not None:
                details.append(f"строк: {format_number(row_count)}")
            if cell_count is not None:
                details.append(f"ячеек: {format_number(cell_count)}")
            suffix = f" ({', '.join(details)})" if details else ""
            lines.append(f"- {sheet}{suffix}")
    else:
        filters = response_data.source.get("filters")
        if isinstance(filters, dict):
            raw_sheet = filters.get("raw_sheet")
            raw_query = filters.get("raw_query")
            if isinstance(raw_sheet, str) and raw_sheet:
                lines.append(f"Лист: {format_dimension_value('raw_sheet', raw_sheet)}")
            if isinstance(raw_query, str) and raw_query:
                lines.append(f"Поиск: {raw_query}")
            if raw_sheet or raw_query:
                lines.append("")

        for row in response_data.table.rows:
            row_number = row.get("row_number")
            row_label = row.get("row_label") or "без названия"
            prefix = f"Строка {format_number(row_number)}" if row_number is not None else "Строка"
            lines.append(f"{prefix}. {row_label}")
            values_preview = row.get("values_preview")
            if isinstance(values_preview, str) and values_preview.strip():
                lines.append(f"Значения: {values_preview}")
            lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

    if response_data.table.truncated:
        lines.append("")
        lines.append(f"Показаны первые {len(response_data.table.rows)} из {response_data.table.total_rows} строк.")

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=[],
        source=response_data.source,
        warnings=response_data.warnings,
    )


def build_model_available_metrics_answer(response_data: ResponseData) -> AnswerDraft | None:
    if response_data.source.get("report_type") != "model":
        return None
    if response_data.source.get("view") != "model_available_metrics":
        return None

    lines = build_answer_header(response_data)
    lines.append("")
    lines.append("Подключенные показатели модели:")
    lines.extend(f"- {METRIC_LABELS.get(metric, metric)}" for metric in MODEL_SAFE_METRICS)
    lines.append("")
    lines.append("Также можно спросить доступные срезы модели, raw-листы модели или безопасные строки raw-листов.")

    return AnswerDraft(
        text="\n".join(lines),
        used_metrics=[],
        source=response_data.source,
        warnings=response_data.warnings,
    )


def build_ready_answer(response_data: ResponseData) -> AnswerDraft:
    roadmap_answer = build_roadmap_answer(response_data)
    if roadmap_answer is not None:
        return roadmap_answer

    model_available_metrics_answer = build_model_available_metrics_answer(response_data)
    if model_available_metrics_answer is not None:
        return model_available_metrics_answer

    model_raw_answer = build_model_raw_answer(response_data)
    if model_raw_answer is not None:
        return model_raw_answer

    table_answer = build_table_answer(response_data)
    if table_answer is not None:
        return table_answer

    lines = build_answer_header(response_data)
    lines.append("")
    if response_data.summary:
        for item in response_data.summary:
            lines.append(format_metric_line(item.metric, item.value, item.unit))
    elif response_data.table and response_data.table.rows:
        row = response_data.table.rows[0]
        units = response_data.source.get("units") if isinstance(response_data.source.get("units"), dict) else {}
        metric_names = [metric for metric in response_data.source.get("metrics", []) if isinstance(metric, str)]
        for metric in metric_names:
            if metric not in row:
                continue
            raw_unit = units.get(metric) if isinstance(units, dict) else None
            if raw_unit is None and response_data.source.get("report_type") in {"payment_calendar", "model", "non_project_expenses", "debt_and_bookings", "stock_for_sale", "sales_report"}:
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
    if key == "source_kind" and isinstance(value, str):
        return SOURCE_KIND_LABELS.get(value, value)
    if key == "property_type" and isinstance(value, str):
        return STOCK_PROPERTY_TYPE_LABELS.get(value, value)
    if key == "segment" and isinstance(value, str):
        return SALES_SEGMENT_LABELS.get(value, value)
    if key == "owner_scope" and isinstance(value, str):
        return SALES_OWNER_LABELS.get(value, value)
    if key == "scenario" and isinstance(value, str):
        return SALES_SCENARIO_LABELS.get(value, value)
    if key == "period_kind" and isinstance(value, str):
        return SALES_PERIOD_KIND_LABELS.get(value, value)
    if key == "value_kind" and isinstance(value, str):
        return AGENTS_VALUE_KIND_LABELS.get(value, value)
    if key == "sheet_kind" and isinstance(value, str):
        return SUMMARY_SHEET_KIND_LABELS.get(value, value)
    if key == "is_in_work":
        return "да" if bool(value) else "нет"
    if key == "metric" and isinstance(value, str):
        return METRIC_LABELS.get(value, value)
    if key == "metric_key" and isinstance(value, str):
        return {
            "sales_revenue": "Продажи",
            "cash_receipts": "Поступления денежных средств",
            "contract_area_sqm": "Площадь контрактации",
            "contract_count": "Количество сделок",
            "price_per_sqm": "Цена за м2",
        }.get(value, METRIC_LABELS.get(value, value))
    if key == "raw_sheet" and isinstance(value, str):
        normalized = " ".join(value.strip().lower().replace("ё", "е").split())
        return RAW_SHEET_LABELS.get(normalized, value)
    if key in {"period", "period_month", "month", "budget_month", "payment_period_month"} and isinstance(value, str) and len(value) >= 7:
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
            if raw_unit is None and response_data.source.get("report_type") in {"payment_calendar", "model", "non_project_expenses", "debt_and_bookings", "stock_for_sale", "sales_report"}:
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
    if response_data and "empty_result" in errors:
        source = response_data.source
        filters = source.get("filters") if isinstance(source.get("filters"), dict) else {}
        step_no = filters.get("step_no") if isinstance(filters, dict) else None
        if source.get("report_type") == "roadmap" and source.get("view") == "step_details" and step_no is not None:
            text = f"Этап {step_no} не найден в дорожной карте за выбранный период."
        else:
            text = "По заданным условиям данных не найдено."
    else:
        text = "Не удалось подготовить проверенный ответ по данным."
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
        if response_data.source.get("report_type") in TEMPLATE_REPORT_TYPES:
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
