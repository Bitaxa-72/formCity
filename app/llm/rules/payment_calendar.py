from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
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
    }
