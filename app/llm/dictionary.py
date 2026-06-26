from enum import StrEnum


class Intent(StrEnum):
    DATA_QUERY = "data_query"
    DIMENSION_QUERY = "dimension_query"
    CONTEXT_QUERY = "context_query"
    MATH_ON_LAST_RESULT = "math_on_last_result"
    CLARIFICATION_ANSWER = "clarification_answer"
    GENERAL_QUESTION = "general_question"
    UNSUPPORTED = "unsupported"


class ReportType(StrEnum):
    SUMMARY = "summary"
    MODEL = "model"
    PAYMENT_CALENDAR = "payment_calendar"
    ROADMAP = "roadmap"
    SALES_REPORT = "sales_report"
    SALES_PLAN_EXECUTION = "sales_plan_execution"
    AGENTS_REPORT = "agents_report"
    STOCK_FOR_SALE = "stock_for_sale"
    DEBT_AND_BOOKINGS = "debt_and_bookings"
    NON_PROJECT_EXPENSES = "non_project_expenses"
    UNKNOWN = "unknown"


class Project(StrEnum):
    OBVODNY = "obvodny"
    MOSKOVSKY = "moskovsky"
    EVGENIEVSKY = "evgenievsky"
    ALL = "all"


class Metric(StrEnum):
    PLAN = "plan"
    FACT = "fact"
    DEVIATION = "deviation"
    DURATION_MIN = "duration_min"
    DURATION_MAX = "duration_max"
    DURATION_RANGE = "duration_range"
    STEP_COUNT = "step_count"
    MODEL_REVENUE = "model_revenue"
    MODEL_COST_OF_SALES = "model_cost_of_sales"
    MODEL_GROSS_PROFIT = "model_gross_profit"
    MODEL_NET_PROFIT = "model_net_profit"
    MODEL_NPV = "model_npv"
    MODEL_ROE = "model_roe"
    MODEL_LLCR = "model_llcr"
    MODEL_TOTAL_AREA = "model_total_area"
    MODEL_UNITS_COUNT = "model_units_count"
    MODEL_PIR = "model_pir"
    AMOUNT = "amount"
    EXECUTED_AMOUNT = "executed_amount"
    REMAINING_AMOUNT = "remaining_amount"


class PaymentCalendarView(StrEnum):
    SUMMARY = "summary"
    DETAILS = "details"
    PAYMENTS = "payments"
    INCOME = "income"
    BALANCE_START = "balance_start"
    BALANCE_END = "balance_end"
    FULL_ROADMAP = "full_roadmap"
    TOTAL_DURATION = "total_duration"
    ROADMAP_STEPS = "roadmap_steps"
    EXTERNAL_STEPS = "external_steps"
    STEP_DETAILS = "step_details"
    MODEL_SUMMARY = "model_summary"
    MODEL_KPI = "model_kpi"
    MODEL_AVAILABLE_METRICS = "model_available_metrics"
    MODEL_AVAILABLE_SNAPSHOTS = "model_available_snapshots"
    NON_PROJECT_EXPENSES_SUMMARY = "non_project_expenses_summary"
    NON_PROJECT_EXPENSES_DETAILS = "non_project_expenses_details"
    NON_PROJECT_EXPENSES_AVAILABLE_PERIODS = "non_project_expenses_available_periods"
    NON_PROJECT_EXPENSES_AVAILABLE_CATEGORIES = "non_project_expenses_available_categories"
    NON_PROJECT_EXPENSES_AVAILABLE_ITEMS = "non_project_expenses_available_items"
    NON_PROJECT_EXPENSES_AVAILABLE_KINDS = "non_project_expenses_available_kinds"


class Dimension(StrEnum):
    ARTICLE = "article"
    ARTICLE_KIND = "article_kind"
    PROJECT = "project"
    PERIOD_MONTH = "period_month"
    STEP = "step"
    EXTERNAL = "external"
    SNAPSHOT_MONTH = "snapshot_month"
    METRIC = "metric"
    ITEM_KIND = "item_kind"
    FM_CATEGORY = "fm_category"
    ITEM_NAME = "item_name"
    ROW_TYPE = "row_type"


class GroupBy(StrEnum):
    PROJECT = "project"
    PERIOD = "period"
    MONTH = "month"
    ARTICLE = "article"
    ARTICLE_KIND = "article_kind"
    QUARTER = "quarter"
    YEAR = "year"
    FLOOR = "floor"
    ROOM_TYPE = "room_type"
    AGENT = "agent"
    BANK = "bank"
    METRIC = "metric"
    ROW_ORDER = "row_order"
    STEP = "step"
    PARENT_STEP = "parent_step"
    ACTION = "action"
    EXTERNAL = "external"
    TOTAL = "total"
    ITEM_KIND = "item_kind"
    FM_CATEGORY = "fm_category"
    ITEM_NAME = "item_name"
    ROW_TYPE = "row_type"


class OperationType(StrEnum):
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    PERCENT = "percent"
    DIFFERENCE = "difference"
    RATIO = "ratio"
    AVERAGE = "average"
    COMPARE_PERIODS = "compare_periods"
    SAME_METRIC_OTHER_PERIOD = "same_metric_other_period"


class OperationSource(StrEnum):
    LAST_RESULT = "last_result"
    DIALOG_STATE = "dialog_state"
    LITERAL = "literal"


REPORT_TYPE_ALIASES: dict[str, list[str]] = {
    ReportType.SUMMARY.value: ["сводный отчет", "сводка", "общий отчет"],
    ReportType.MODEL.value: ["модель", "финансовая модель"],
    ReportType.PAYMENT_CALENDAR.value: ["платежный календарь", "платежи", "план факт платежей", "отклонение по платежам"],
    ReportType.ROADMAP.value: ["дорожная карта", "roadmap", "роадмап"],
    ReportType.SALES_REPORT.value: ["отчет о продажах", "продажи", "выручка", "сделки", "квадратные метры"],
    ReportType.SALES_PLAN_EXECUTION.value: ["исполнение плана продаж", "план продаж", "выполнение плана продаж"],
    ReportType.AGENTS_REPORT.value: ["отчет по агентам", "агенты", "агентское вознаграждение"],
    ReportType.STOCK_FOR_SALE.value: ["остатки в продаже", "остатки", "склад", "экспозиция"],
    ReportType.DEBT_AND_BOOKINGS.value: ["дз и брони", "дз", "дебиторка", "долги", "брони", "бронирования"],
    ReportType.NON_PROJECT_EXPENSES.value: ["непроектные расходы", "расходы вне проекта", "общие расходы"],
}


REPORT_RULES: dict[str, object] = {
    ReportType.MODEL.value: {
        "metrics": {
            Metric.MODEL_REVENUE.value: ["выручка", "доход", "продажи в деньгах"],
            Metric.MODEL_COST_OF_SALES.value: ["себестоимость", "себестоимость продаж"],
            Metric.MODEL_GROSS_PROFIT.value: ["валовая прибыль", "gross profit"],
            Metric.MODEL_NET_PROFIT.value: ["чистая прибыль", "net profit"],
            Metric.MODEL_NPV.value: ["npv", "нпв"],
            Metric.MODEL_ROE.value: ["roe", "рентабельность капитала"],
            Metric.MODEL_LLCR.value: ["llcr"],
            Metric.MODEL_TOTAL_AREA.value: ["общая площадь", "площадь зданий"],
            Metric.MODEL_UNITS_COUNT.value: ["количество помещений", "помещения", "штуки"],
            Metric.MODEL_PIR.value: ["пир", "проектно изыскательские работы"],
        },
        "views": {
            PaymentCalendarView.MODEL_SUMMARY.value: {
                "aliases": ["модель", "краткая модель", "сводка модели", "итоги модели"],
                "meaning": "краткая сводка основных KPI модели по последнему доступному срезу",
            },
            PaymentCalendarView.MODEL_KPI.value: {
                "aliases": ["kpi", "показатели модели", "метрики модели"],
                "meaning": "верхнеуровневые показатели модели",
            },
            PaymentCalendarView.MODEL_AVAILABLE_METRICS.value: {
                "aliases": ["какие показатели", "доступные показатели", "что есть в модели", "какие метрики"],
                "meaning": "список доступных показателей модели",
            },
            PaymentCalendarView.MODEL_AVAILABLE_SNAPSHOTS.value: {
                "aliases": ["какие срезы", "какие версии модели", "доступные месяцы модели", "доступные срезы"],
                "meaning": "список доступных срезов модели",
            },
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие срезы", "доступные срезы", "какие версии модели"],
            Dimension.METRIC.value: ["какие показатели", "список показателей", "доступные показатели"],
        },
        "group_by": {
            GroupBy.MONTH.value: ["по срезам", "по месяцам модели", "по версиям модели"],
            GroupBy.METRIC.value: ["по показателям", "все показатели"],
        },
    },
    ReportType.NON_PROJECT_EXPENSES.value: {
        "metrics": {
            Metric.AMOUNT.value: ["сумма", "начислено", "общая сумма", "плановая сумма"],
            Metric.EXECUTED_AMOUNT.value: ["исполнено", "оплачено", "факт", "выполнено"],
            Metric.REMAINING_AMOUNT.value: ["остаток", "прогноз", "остаток прогноз", "осталось"],
        },
        "metric_bundles": {
            "full": {
                "aliases": ["итоги", "итог", "все показатели", "сводка", "полный отчет"],
                "metrics": [Metric.AMOUNT.value, Metric.EXECUTED_AMOUNT.value, Metric.REMAINING_AMOUNT.value],
            },
        },
        "views": {
            PaymentCalendarView.NON_PROJECT_EXPENSES_SUMMARY.value: {
                "aliases": ["непроектные расходы", "сводка непроектных расходов", "итоги непроектных расходов"],
                "meaning": "сводка непроектных расходов по категориям",
            },
            PaymentCalendarView.NON_PROJECT_EXPENSES_DETAILS.value: {
                "aliases": ["детально", "подробно", "по строкам", "по всем строкам", "детализация"],
                "meaning": "детальные строки непроектных расходов",
            },
            PaymentCalendarView.NON_PROJECT_EXPENSES_AVAILABLE_PERIODS.value: {
                "aliases": ["какие периоды", "доступные периоды", "какие месяцы", "какие срезы"],
                "meaning": "список доступных периодов непроектных расходов",
            },
            PaymentCalendarView.NON_PROJECT_EXPENSES_AVAILABLE_CATEGORIES.value: {
                "aliases": ["какие категории", "список категорий", "категории непроектных расходов", "что есть по категориям"],
                "meaning": "список категорий из поля в ФМ",
            },
            PaymentCalendarView.NON_PROJECT_EXPENSES_AVAILABLE_ITEMS.value: {
                "aliases": ["какие строки", "список строк", "что есть", "какие статьи", "список статей"],
                "meaning": "список строк непроектных расходов",
            },
            PaymentCalendarView.NON_PROJECT_EXPENSES_AVAILABLE_KINDS.value: {
                "aliases": ["какие типы", "типы строк", "разделы", "типы расходов"],
                "meaning": "список типов строк непроектных расходов",
            },
        },
        "filters": {
            Dimension.ITEM_KIND.value: {
                "lost_income": ["недополученные доходы", "упущенные доходы"],
                "debt_receivable": ["дз", "дебиторка", "долги"],
                "non_project_expenses_total": ["итог непроектных расходов", "всего непроектные расходы"],
                "personal": ["личное"],
                "admin_expenses": ["ахр", "административные расходы"],
                "evgenievsky": ["евг", "евгеньевский"],
                "legal_entity": ["юрлица", "юридические лица", "ооо"],
                "fit_out": ["отделочные работы", "отделка"],
                "commercial": ["коммерческие расходы"],
                "furniture": ["мебелировка", "мебель"],
                "construction": ["строительные работы", "стройка"],
                "developer_maintenance": ["содержание застройщика"],
                "object_maintenance": ["содержание объекта", "техзаказчик"],
                "finance": ["финансовые расходы"],
                "pir": ["пир", "проектные работы"],
                "other_income_expense": ["прочие доходы и расходы", "прочие"],
            },
            Dimension.FM_CATEGORY.value: {
                "type": "free_text_search",
                "examples": ["коммерческие расходы", "ПИР", "финансовые расходы"],
            },
            Dimension.ITEM_NAME.value: {
                "type": "free_text_search",
                "examples": ["ДЗ", "Личное", "ЕВГ"],
            },
        },
        "group_by": {
            GroupBy.FM_CATEGORY.value: ["по категориям", "в разрезе категорий", "по фм"],
            GroupBy.ITEM_KIND.value: ["по типам", "по разделам", "по типам строк"],
            GroupBy.ITEM_NAME.value: ["по строкам", "по статьям", "детально"],
            GroupBy.MONTH.value: ["по месяцам", "помесячно"],
        },
        "dimensions": {
            Dimension.PERIOD_MONTH.value: ["какие периоды", "доступные периоды", "какие месяцы"],
            Dimension.FM_CATEGORY.value: ["какие категории", "список категорий"],
            Dimension.ITEM_NAME.value: ["какие строки", "список строк", "какие статьи"],
            Dimension.ITEM_KIND.value: ["какие типы", "типы строк", "разделы"],
        },
    },
    ReportType.PAYMENT_CALENDAR.value: {
        "metrics": {
            Metric.PLAN.value: ["план", "плановый"],
            Metric.FACT.value: ["факт", "фактический", "оплачено"],
            Metric.DEVIATION.value: ["отклонение", "разница"],
        },
        "metric_bundles": {
            "full": {
                "aliases": ["итоги", "итог", "план факт", "план/факт", "полный отчет"],
                "metrics": [Metric.PLAN.value, Metric.FACT.value, Metric.DEVIATION.value],
            },
        },
        "views": {
            PaymentCalendarView.SUMMARY.value: {
                "aliases": ["итоги", "итог", "сводка", "общая картина", "план факт", "план/факт"],
                "meaning": "итоговые строки платежного календаря: остаток на начало, поступления, итого платежи, остаток на конец",
            },
            PaymentCalendarView.DETAILS.value: {
                "aliases": ["подробный отчет", "детализация", "детально", "по всем статьям", "разбивка по статьям"],
                "meaning": "детальные статьи расходов",
            },
            PaymentCalendarView.PAYMENTS.value: {
                "aliases": ["расходы", "платежи", "итого платежи", "платежи всего", "всего платежи"],
                "meaning": "строка ИТОГО платежи",
            },
            PaymentCalendarView.INCOME.value: {
                "aliases": ["поступления", "приход", "входящие платежи"],
                "meaning": "строка Поступления",
            },
            PaymentCalendarView.BALANCE_START.value: {
                "aliases": ["остаток на начало", "остаток дс на начало", "остаток денег на начало"],
                "meaning": "строка Остаток ДС на начало месяца",
            },
            PaymentCalendarView.BALANCE_END.value: {
                "aliases": ["остаток на конец", "остаток дс на конец", "остаток денег на конец"],
                "meaning": "строка Остаток ДС на конец месяца",
            },
        },
        "filters": {
            Dimension.ARTICLE.value: {
                "type": "free_text_search",
                "examples": ["реклама", "аренда", "зарплата", "налоги"],
            },
            Dimension.ARTICLE_KIND.value: {
                "income_total": ["поступления", "приход", "входящие платежи"],
                "payment_total": ["итого платежи", "платежи всего", "всего платежи", "общие платежи"],
                "detail": ["расходы", "статьи расходов", "детальные расходы"],
                "balance_start": ["остаток на начало", "остаток дс на начало"],
                "balance_end": ["остаток на конец", "остаток дс на конец"],
            },
        },
        "group_by": {
            GroupBy.ARTICLE.value: ["по всем статьям", "разбивка по статьям", "детализация по статьям", "в разрезе статей"],
            GroupBy.ARTICLE_KIND.value: ["по типам строк", "по категориям строк"],
            GroupBy.MONTH.value: ["по месяцам", "помесячно"],
            GroupBy.PROJECT.value: ["по проектам", "в разрезе проектов"],
        },
        "dimensions": {
            Dimension.ARTICLE.value: ["какие статьи", "список статей", "доступные статьи"],
            Dimension.ARTICLE_KIND.value: ["какие типы строк", "типы строк"],
            Dimension.PROJECT.value: ["какие проекты", "список проектов"],
            Dimension.PERIOD_MONTH.value: ["какие месяцы", "доступные периоды"],
        },
    },
    ReportType.ROADMAP.value: {
        "metrics": {
            Metric.DURATION_MIN.value: ["минимальный срок", "минимум дней", "min срок"],
            Metric.DURATION_MAX.value: ["максимальный срок", "максимум дней", "max срок"],
            Metric.DURATION_RANGE.value: ["срок", "сроки", "сколько дней", "сколько занимает"],
            Metric.STEP_COUNT.value: ["сколько этапов", "количество этапов"],
        },
        "views": {
            PaymentCalendarView.FULL_ROADMAP.value: {
                "aliases": ["дорожная карта", "полная дорожная карта", "все этапы", "покажи дорожную карту"],
                "meaning": "полный список этапов дорожной карты",
            },
            PaymentCalendarView.TOTAL_DURATION.value: {
                "aliases": ["сколько дней", "сколько занимает", "итоговый срок", "общий срок", "срок вывода из залога"],
                "meaning": "итоговая строка со сроком 9-15 рабочих дней",
            },
            PaymentCalendarView.EXTERNAL_STEPS.value: {
                "aliases": ["банк", "росреестр", "внешние этапы", "зависит от банка", "зависит от росреестра"],
                "meaning": "этапы, зависящие от внешних участников",
            },
            PaymentCalendarView.STEP_DETAILS.value: {
                "aliases": ["этап", "номер этапа", "подробности этапа"],
                "meaning": "конкретный этап дорожной карты",
            },
        },
        "dimensions": {
            Dimension.PERIOD_MONTH.value: ["какие периоды", "доступные периоды", "какие месяцы"],
            Dimension.STEP.value: ["какие этапы", "список этапов"],
        },
    },
}


def build_llm_dictionary() -> dict[str, object]:
    return {
        "intent": [item.value for item in Intent],
        "report_type": [item.value for item in ReportType],
        "report_type_aliases": REPORT_TYPE_ALIASES,
        "report_rules": REPORT_RULES,
        "project": [item.value for item in Project],
        "metric": [item.value for item in Metric],
        "payment_calendar_view": [
            PaymentCalendarView.SUMMARY.value,
            PaymentCalendarView.DETAILS.value,
            PaymentCalendarView.PAYMENTS.value,
            PaymentCalendarView.INCOME.value,
            PaymentCalendarView.BALANCE_START.value,
            PaymentCalendarView.BALANCE_END.value,
        ],
        "report_view": [item.value for item in PaymentCalendarView],
        "dimension": [item.value for item in Dimension],
        "group_by": [item.value for item in GroupBy],
        "operation_type": [item.value for item in OperationType],
        "operation_source": [item.value for item in OperationSource],
    }
