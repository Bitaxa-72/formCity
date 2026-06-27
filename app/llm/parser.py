import json
from typing import Any, Literal

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.core.config import Settings
from app.llm.chat_options import build_chat_completion_options
from app.llm.dictionary import (
    Dimension,
    GroupBy,
    Intent,
    Metric,
    OperationSource,
    OperationType,
    PaymentCalendarView,
    Project,
    ReportType,
)
from app.llm.input import LLMInput


PARSER_SYSTEM_PROMPT = """
You parse Russian user messages into strict backend JSON for an analytics Telegram bot.
Return only valid JSON.
Do not add explanations.
Do not calculate numbers.
Do not invent data.
Do not generate SQL.
Use only enum values from dictionary in the user payload.
Free text is allowed only inside filters when the backend must search the database.
Use state_delta only for context changes.

Core concepts:
- report_type is the report area.
- project is the project scope.
- period is the time filter.
- metrics are numeric values to calculate.
- view is a named report view that backend expands into filters, group_by, and metrics.
- filters restrict what exact entity or category to search.
- group_by splits the result into multiple rows.
- dimension asks for a list of available values without numeric calculation.

Intent rules:
- data_query: the user asks to calculate data.
- dimension_query: the user asks for available values, lists, or options.
- context_query: the user changes previous request context.
- clarification_answer: the user answers the bot clarification question.
- math_on_last_result: the user asks to calculate from the previous result.
- general_question: greeting or general bot question.
- unsupported: the request is outside analytics.

Clarification rules:
- If dialog_state.awaiting_clarification is true, the user message is usually clarification_answer.
- In clarification_answer, return only newly clarified fields and obvious filters from the message.
- Do not add period.mode="all" when the user answers a clarification and did not ask for all time.
- Do not repeat old fields that are not present in the user message.
- If the clarification message contains a concrete filter, put it into filters.

Report type rules:
- Use report_type_aliases and report_rules to recognize report_type.
- If the user clearly names a report type or alias, always set report_type.
- Do not return null report_type when a clear alias is present.

Metric rules:
- metrics are only numeric values.
- If the user asks for plan, fact, or deviation, use matching values from dictionary.metric.
- If the user asks for totals, summary, plan/fact, or full report, use a metric bundle from report_rules when available.
- If the metric is unclear, set needs_clarification=true.

Payment calendar view rules:
- For "итоги", "итог", "сводка", "общая картина", set view="summary".
- For "подробный отчет", "детализация", "по всем статьям", set view="details".
- For "поступления", "приход", set view="income".
- For "итого платежи", "платежи всего", "расходы", set view="payments".
- For "остаток на начало", set view="balance_start".
- For "остаток на конец", set view="balance_end".
- If the user asks only "остаток" without start/end direction, set needs_clarification=true and ask whether they need start or end balance.
- For payment_calendar views, also set metrics=["plan","fact","deviation"] unless the user explicitly asks only one metric.
- Do not use filters.article_kind for these views; backend applies report view rules.
- If the user names a concrete article like "реклама" or "ФОТ", use filters.article and do not set view.

Filter rules:
- filters are used when the user limits the request to a concrete entity or category.
- Phrases like "по рекламе", "по аренде", "по зарплате", "по налогам" mean a concrete filter, not grouping.
- For those phrases use filters.article when article is available for the current report_type.
- filters.article may contain the user's free text search phrase.
- If report_rules contains a matching filter alias, use that filter.

Group by rules:
- group_by is used only when the user asks for breakdown, split, detail, or section.
- Use group_by=["article"] for phrases like "по всем статьям", "разбивка по статьям", "детализация по статьям", "в разрезе статей".
- Do not use group_by=["article"] for "по рекламе"; that is filters.article.

Dimension rules:
- Use dimension_query when the user asks for a list without numeric calculation.
- If the user asks for a list of expenses and report_rules has an expense category filter, include that filter.
- "какие статьи есть в платежном календаре" means dimension="article".
- "какие статьи расходов есть в платежном календаре" means dimension="article" and filters.article_kind="detail".
- "какие проекты есть в платежном календаре" means dimension="project".
- "какие периоды есть в платежном календаре" means dimension="period_month".
- "какие типы строк есть в платежном календаре" means dimension="article_kind".


Summary report rules:
- For report_type="summary", use only safe aggregate views. Never request or output personal rows, FIO, contacts, managers, agents, unit numbers, DDU, DKP, contract numbers, bookings, notes, passports, or requisites.
- "сводный отчет", "сводная", "сводные таблицы" means view="summary_overview" and metrics=["summary_sheet_count","summary_row_count","summary_cell_count"].
- "суммы", "числовые значения", "агрегаты" means view="summary_values" and metrics=["summary_numeric_cell_count","summary_value_sum"].
- If the user names a safe column like "оплачено", "остаток", "площадь", "цена за метр", use view="summary_values", metrics=["summary_value_sum"], filters.header_key with the matching dictionary value.
- If the user asks "какие проекты" for summary, use intent="dimension_query", view="summary_available_projects", dimension="project".
- "какие файлы", "источники" means intent="dimension_query", view="summary_available_files", dimension="source_file".
- "какие листы" means intent="dimension_query", view="summary_available_sheets", dimension="sheet_name".
- "типы листов", "виды листов", "разделы" means intent="dimension_query", view="summary_available_sheet_kinds", dimension="sheet_kind".
- "какие колонки", "какие поля", "какие показатели" means intent="dimension_query", view="summary_available_headers", dimension="header_key".
- "типы строк", "виды строк" means intent="dimension_query", view="summary_available_row_types", dimension="row_type".
- For "апартаменты", "коммерция", "кладовки", "уступки", "расторжения", "аренда", "классы", "даты" in summary, use filters.sheet_kind from report_rules.
- Summary has no single period filter; omit period unless the user clearly asks another report.

Roadmap rules:
- For report_type="roadmap", use views instead of payment_calendar metrics.
- "дорожная карта", "покажи дорожную карту", "все этапы" means view="full_roadmap".
- "сколько дней", "сколько занимает", "итоговый срок", "срок вывода из залога" means view="total_duration" and metrics=["duration_min","duration_max"].
- "банк", "росреестр", "внешние этапы", "зависит от банка" means view="external_steps".
- If the roadmap user specifically says "банк", also set filters.action_text_contains="БАНК".
- If the roadmap user specifically says "росреестр", also set filters.action_text_contains="РОСРЕЕСТР".
- "какие периоды есть по дорожной карте" means intent="dimension_query", dimension="period_month".
- If the user asks for a numbered roadmap step, use view="step_details" and filters.step_no=<number>.
- If no roadmap period is specified, omit period; backend will use the latest available month and tell the user.

Model raw rules:
- For report_type="model", "какие листы", "список листов", "какие таблицы есть" means intent="dimension_query", view="model_raw_sheets", dimension="raw_sheet".
- For "финмодель", "лист финмодель", "остатки", "лист остатки", "для консолидации", set view="model_raw_rows" and filters.raw_sheet to the mentioned sheet phrase.
- For "найди", "поиск", "строка", "значение" inside a model raw sheet, set view="model_raw_search"; put the search phrase into filters.raw_query and sheet phrase into filters.raw_sheet when present.
- For model raw views, do not set metrics.
- If no model period is specified, omit period; backend will use the latest available model snapshot and tell the user.

Debt and bookings rules:
- For report_type="debt_and_bookings", never request or output client names, contacts, managers, comments, document numbers, or refusal reasons.
- Unit numbers are allowed for debt_and_bookings as dimension="unit_number", group_by=["unit_number"], filters.unit_number, or filters.unit_number_contains.
- "ДЗ и брони", "дебиторка и брони", "итоги ДЗ и броней" means view="debt_bookings_summary" and metrics=["debt_item_count","debt_total_amount"].
- "брони" means view="debt_bookings_bookings".
- "просроченные", "просрочка" means view="debt_bookings_overdue".
- "текущие" means view="debt_bookings_current".
- "зарегистрировано", "зарегистрированные" means view="debt_bookings_registered".
- "помесячно", "по месяцам", "график" means view="debt_bookings_monthly" and metrics=["debt_monthly_value"].
- "отклонения", "план факт", "факт оплат", "остаток по оплатам" means view="debt_bookings_deviations" and metrics=["debt_plan_amount","debt_updated_plan_amount","debt_fact_payment_amount","debt_remaining_amount"].
- "отказы" means view="debt_bookings_refusals" and metrics=["debt_refusal_count","debt_refusal_area","debt_refusal_full_price"].
- "какие периоды есть по ДЗ и броням" means intent="dimension_query", view="debt_bookings_available_periods", dimension="snapshot_month".
- "какие типы", "какие разделы" for debt_and_bookings means intent="dimension_query", view="debt_bookings_available_kinds", dimension="item_kind".
- "номера помещений", "какие помещения" for debt_and_bookings means intent="dimension_query", view="debt_bookings_available_unit_numbers", dimension="unit_number".
- "статусы отказов" means intent="dimension_query", view="debt_bookings_available_statuses", dimension="status".
- "способы оплаты" means intent="dimension_query", view="debt_bookings_available_payment_types", dimension="payment_type".
- If no debt_and_bookings period is specified, omit period; backend will use all available snapshots unless a view says otherwise.

Stock for sale rules:
- For report_type="stock_for_sale", use snapshot_month as the period.
- "остатки в продаже", "экспозиция", "сводка остатков" means view="stock_summary".
- "суммы", "ДДУ", "ДУПТ", "наценка" means view="stock_amounts".
- "цена за метр", "цена м2", "цены за м2" means view="stock_price_per_sqm".
- "по этажам", "разбивка по этажам" means view="stock_by_floors".
- "в работе" means view="stock_in_work".
- "апартаменты" means view="stock_apartments".
- "кладовые" means view="stock_storage".
- "рестораны" means view="stock_restaurants".
- "первый этаж", "1 этаж" means view="stock_first_floor".
- "какие периоды есть по остаткам" means intent="dimension_query", view="stock_available_periods", dimension="snapshot_month".
- "какие типы объектов" means intent="dimension_query", view="stock_available_property_types", dimension="property_type".
- "какие этажи" means intent="dimension_query", view="stock_available_floors", dimension="floor_number".
- If no stock_for_sale period is specified, omit period; backend will use the latest available snapshot and tell the user.

Sales report rules:
- For report_type="sales_report", distinguish report snapshot and sales period.
- If the user says "срез", "версия отчета", or "на дату", put that month into state_delta.period.
- If the user asks "за май", "за март", or another ordinary month without saying "срез", put it into filters.period_month as YYYY-MM-01, not state_delta.period.
- "отчет о продажах", "продажи", "сводка продаж" means view="sales_summary".
- "по сегментам", "по типам помещений", "разбивка" means view="sales_by_segments".
- "помесячно", "по месяцам", "динамика продаж" means view="sales_monthly".
- "оплаты", "оплаты по ДДУ", "остаток по ДДУ" means view="sales_payments".
- "цена за метр", "цена м2" means view="sales_price_per_sqm".
- "апартаменты", "кладовки", "ресторан", "коммерция 1 этаж", "коммерция 2 этаж", "SH" mean the matching sales segment view.
- "выручка" means metrics=["sales_contract_revenue"].
- "квадратные метры", "площадь", "м2" means metrics=["sales_contract_area_sqm"].
- "сделки", "количество" means metrics=["sales_contract_count"].
- "факт" means filters.scenario="fact"; "план" means filters.scenario="plan".
- "какие срезы есть по продажам" means intent="dimension_query", view="sales_available_snapshots", dimension="snapshot_month".
- "какие месяцы продаж" means intent="dimension_query", view="sales_available_periods", dimension="period_month".
- "какие сегменты" means intent="dimension_query", view="sales_available_segments", dimension="segment".
- "какие показатели" means intent="dimension_query", view="sales_available_metrics", dimension="metric_key".
- If no sales report snapshot is specified, omit period; backend will use the latest available report snapshot and tell the user.

Sales plan execution rules:
- For report_type="sales_plan_execution", the period is the report snapshot month. If no period is specified, omit period; backend will use the latest available snapshot and tell the user.
- "исполнение плана продаж", "план продаж", "выполнение плана продаж" means view="sales_plan_summary".
- "по сегментам", "по типам помещений", "разбивка" means view="sales_plan_by_segments".
- "месячный блок", "за месяц", "конкретный месяц" means view="sales_plan_month".
- "итого год", "за год", "итого 2026" means view="sales_plan_year".
- "весь проект", "итого проект", "общий итог" means view="sales_plan_lifetime".
- "цена за метр", "цена м2" means view="sales_plan_price_per_sqm".
- "апартаменты", "апарты", "ресторан" mean the matching sales_plan segment view.
- "продажи", "выручка" means metrics=["sales_plan_revenue"].
- "поступления", "денежные средства", "ДС" means metrics=["sales_plan_cash_receipts"].
- "квадратные метры", "площадь", "м2" means metrics=["sales_plan_contract_area_sqm"].
- "сделки", "количество" means metrics=["sales_plan_contract_count"].
- "план" means filters.scenario="plan"; "факт" means filters.scenario="fact"; "прогноз" means filters.scenario="forecast"; "отклонение" means filters.scenario="deviation"; "остаток к продаже" means filters.scenario="remaining_to_sell".
- "застройщик" means filters.owner_scope="developer"; "велл" means filters.owner_scope="well".
- "какие срезы есть по исполнению плана продаж" means intent="dimension_query", view="sales_plan_available_snapshots", dimension="snapshot_month".
- "какие сегменты" means intent="dimension_query", view="sales_plan_available_segments", dimension="segment".
- "какие показатели" means intent="dimension_query", view="sales_plan_available_metrics", dimension="metric_key".
- "какие сценарии" means intent="dimension_query", view="sales_plan_available_scenarios", dimension="scenario".
- "какие блоки" means intent="dimension_query", view="sales_plan_available_blocks", dimension="block_kind".

Agents report rules:
- For report_type="agents_report", never request or output agent names, buyer names, contacts, unit numbers, DDU numbers, act numbers, document numbers, notes, or comments.
- "отчет по агентам", "агенты", "агентские вознаграждения", "сводка агентского отчета" means view="agents_summary".
- "помесячно", "по месяцам", "график оплат", "график ДДУ", "график уступки" means view="agents_monthly" and metrics=["agents_monthly_value"].
- "по бюджетным месяцам", "бюджетные месяцы" means view="agents_by_budget_month".
- "ДДУ", "уступка", "меблировка" may be used only for safe aggregate sums; then use view="agents_ddu".
- "количество сделок" means metrics=["agents_deal_count"].
- "площадь", "квадратные метры", "м2" means metrics=["agents_area_sqm"].
- "вознаграждение" means metrics=["agents_commission_amount"].
- "оплачено", "оплаты" means metrics=["agents_paid_amount"].
- "остаток к оплате" means metrics=["agents_remaining_amount"].
- "какие срезы есть по агентам" means intent="dimension_query", view="agents_available_snapshots", dimension="snapshot_month".
- "какие бюджетные месяцы" means intent="dimension_query", view="agents_available_budget_months", dimension="budget_month".
- "какие месяцы оплат", "периоды оплат" means intent="dimension_query", view="agents_available_payment_months", dimension="payment_period_month".
- "какие графики", "типы графиков" means intent="dimension_query", view="agents_available_value_kinds", dimension="value_kind".
- If no agents report snapshot is specified, omit period; backend will use the latest available snapshot and tell the user.

Period rules:
- Put month names and dates into state_delta.period.
- "март" means period.label="март".
- "май 2026" means period.label="май 2026".
- If this is a new independent data_query and no period is specified, period.mode="all" is allowed.
- If this is clarification_answer and no period is specified, omit period.

Examples:

User: "платежный календарь март итоги"
JSON:
{
  "intent": "data_query",
    "state_delta": {
        "report_type": "payment_calendar",
        "period": {"label": "март"},
        "view": "summary",
        "metrics": ["plan", "fact", "deviation"]
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}

User: "факт по рекламе"
If dialog_state.awaiting_clarification is true:
{
  "intent": "clarification_answer",
  "state_delta": {
    "metrics": ["fact"],
    "filters": {"article": "реклама"}
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}

User: "покажи факт по рекламе за май в платежном календаре"
JSON:
{
  "intent": "data_query",
  "state_delta": {
    "report_type": "payment_calendar",
    "period": {"label": "май"},
    "metrics": ["fact"],
    "filters": {"article": "реклама"}
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}

User: "план факт отклонение по статьям за май"
JSON:
{
  "intent": "data_query",
  "state_delta": {
    "period": {"label": "май"},
    "metrics": ["plan", "fact", "deviation"],
    "group_by": ["article"]
  },
  "operation": null,
  "needs_clarification": false,
  "clarification_question": null,
  "confidence": 0.9
}
"""

REPAIR_SYSTEM_PROMPT = """
Fix backend JSON so it matches the required schema.
Return only valid JSON.
Do not change the user's intent.
Do not add facts, numbers, SQL, or explanations.
Use only existing values from invalid_json unless a missing technical field is required by schema.
Allowed top-level keys: intent, state_delta, operation, needs_clarification, clarification_question, confidence.
"""


class LLMParserError(RuntimeError):
    pass


class PeriodDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mode: Literal["all"] | None = None
    from_date: str | None = Field(default=None, alias="from")
    to: str | None = None
    label: str | None = None


class StateDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: ReportType | None = None
    project: Project | None = None
    period: PeriodDelta | None = None
    metrics: list[Metric] | None = None
    view: PaymentCalendarView | None = None
    dimension: Dimension | None = None
    filters: dict[str, Any] | None = None
    group_by: list[GroupBy] | None = None

    def has_updates(self) -> bool:
        return bool(self.model_dump(exclude_none=True))


class OperationOperand(BaseModel):
    source: OperationSource
    metric: Metric | None = None
    value: int | float | str | None = None

    @model_validator(mode="after")
    def validate_operand(self) -> "OperationOperand":
        if self.source == OperationSource.LITERAL and self.value is None:
            raise ValueError("literal operand requires value")
        if self.source in {OperationSource.LAST_RESULT, OperationSource.DIALOG_STATE} and self.metric is None:
            raise ValueError("state/result operand requires metric")
        return self


class Operation(BaseModel):
    type: OperationType
    left: OperationOperand | None = None
    right: OperationOperand | None = None

    @model_validator(mode="after")
    def validate_operation(self) -> "Operation":
        if self.left is None:
            raise ValueError("operation requires left operand")
        if self.type != OperationType.AVERAGE and self.right is None:
            raise ValueError("operation requires right operand")
        return self


class LLMParsedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    state_delta: StateDelta = Field(default_factory=StateDelta)
    operation: Operation | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    confidence: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_response(self) -> "LLMParsedResponse":
        if self.needs_clarification and not self.clarification_question:
            raise ValueError("clarification_question is required")
        if self.intent == Intent.MATH_ON_LAST_RESULT and self.operation is None:
            raise ValueError("math_on_last_result requires operation")
        if self.intent in {Intent.DATA_QUERY, Intent.DIMENSION_QUERY} and not self.state_delta.has_updates() and not self.needs_clarification:
            raise ValueError("data/dimension query requires state_delta")
        return self


def has_concrete_period(period: dict[str, Any]) -> bool:
    label = str(period.get("label") or "").strip().lower()
    if period.get("from") or period.get("to"):
        return True
    if label and label not in {"весь период", "весь доступный период", "all", "whole period"}:
        return True
    return False


def normalize_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    state_delta = normalized.get("state_delta")

    if isinstance(state_delta, dict) and state_delta:
        intent = normalized.get("intent")
        if intent in {"generate_report", "report", "query", "get_data", "get_report"}:
            normalized["intent"] = Intent.DIMENSION_QUERY.value if state_delta.get("dimension") and not state_delta.get("metrics") else Intent.DATA_QUERY.value

    if "intent" not in normalized and isinstance(state_delta, dict) and state_delta:
        if state_delta.get("dimension") and not state_delta.get("metrics"):
            normalized["intent"] = Intent.DIMENSION_QUERY.value
        else:
            normalized["intent"] = Intent.DATA_QUERY.value

    if isinstance(state_delta, dict) and isinstance(state_delta.get("period"), dict):
        period = dict(state_delta["period"])
        if period.get("mode") == "all" and has_concrete_period(period):
            period.pop("mode", None)
            state_delta = dict(state_delta)
            state_delta["period"] = period
            normalized["state_delta"] = state_delta

    return normalized


def format_validation_errors(error: ValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": list(item.get("loc", [])),
            "type": item.get("type"),
            "msg": item.get("msg"),
        }
        for item in error.errors()
    ]


def build_repair_payload(invalid_payload: Any, error: Exception) -> str:
    if isinstance(error, ValidationError):
        errors: Any = format_validation_errors(error)
    elif isinstance(error, json.JSONDecodeError):
        errors = [
            {
                "loc": [],
                "type": "json_decode_error",
                "msg": str(error),
            },
        ]
    else:
        errors = [
            {
                "loc": [],
                "type": type(error).__name__,
                "msg": str(error),
            },
        ]

    return json.dumps(
        {
            "invalid_json": invalid_payload,
            "validation_errors": errors,
            "repair_rules": [
                "Return one JSON object only.",
                "Keep the same semantic meaning.",
                "Add missing required technical fields when obvious.",
                "Remove unknown fields.",
                "Use only allowed dictionary enum values.",
            ],
            "schema_shape": {
                "intent": "required enum",
                "state_delta": "object",
                "operation": "object or null",
                "needs_clarification": "boolean",
                "clarification_question": "string or null",
                "confidence": "number from 0 to 1",
            },
        },
        ensure_ascii=False,
    )


class OpenAILLMParser:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def request_json(self, client: AsyncOpenAI, messages: list[dict[str, str]]) -> str:
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            response_format={"type": "json_object"},
            messages=messages,
            **build_chat_completion_options(self.settings.openai_model),
        )
        content = response.choices[0].message.content
        if not content:
            raise LLMParserError("LLM returned empty content")
        return content

    def validate_payload(self, payload: dict[str, Any]) -> LLMParsedResponse:
        return LLMParsedResponse.model_validate(normalize_llm_payload(payload))

    async def repair_payload(
        self,
        client: AsyncOpenAI,
        invalid_payload: Any,
        error: Exception,
    ) -> dict[str, Any]:
        content = await self.request_json(
            client,
            [
                {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": build_repair_payload(invalid_payload, error)},
            ],
        )
        try:
            repaired_payload = json.loads(content)
        except json.JSONDecodeError as error:
            raise LLMParserError("LLM repair returned invalid JSON") from error
        if not isinstance(repaired_payload, dict):
            raise LLMParserError("LLM repair returned non-object JSON")
        return repaired_payload

    async def parse(self, llm_input: LLMInput) -> LLMParsedResponse:
        if not self.settings.openai_key:
            raise LLMParserError("OPENAI_KEY is not configured")
        if not self.settings.openai_model:
            raise LLMParserError("OPENAI_MODEL is not configured")

        async with httpx.AsyncClient(timeout=30, proxy=self.settings.proxy) as http_client:
            client = AsyncOpenAI(api_key=self.settings.openai_key, http_client=http_client)
            content = await self.request_json(
                client,
                [
                    {"role": "system", "content": PARSER_SYSTEM_PROMPT},
                    {"role": "user", "content": llm_input.model_dump_json(by_alias=True)},
                ],
            )

            try:
                payload = json.loads(content)
            except json.JSONDecodeError as error:
                repaired_payload = await self.repair_payload(client, content, error)
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error

            if not isinstance(payload, dict):
                repaired_payload = await self.repair_payload(
                    client,
                    payload,
                    ValueError("LLM returned non-object JSON"),
                )
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error

            try:
                return self.validate_payload(payload)
            except ValidationError as error:
                repaired_payload = await self.repair_payload(client, payload, error)
                try:
                    return self.validate_payload(repaired_payload)
                except ValidationError as repair_error:
                    raise LLMParserError("LLM repair returned invalid schema") from repair_error
