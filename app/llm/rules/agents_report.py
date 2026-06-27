from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.AGENTS_DEAL_COUNT.value: ["количество сделок", "сколько сделок", "число сделок"],
            Metric.AGENTS_AREA_SQM.value: ["площадь", "квадратные метры", "метры"],
            Metric.AGENTS_COMMISSION_BASE_AMOUNT.value: ["база вознаграждения", "цена сделки для расчета"],
            Metric.AGENTS_COMMISSION_AMOUNT.value: ["агентское вознаграждение", "вознаграждение", "сумма вознаграждения"],
            Metric.AGENTS_ACT_TOTAL_AMOUNT.value: ["сумма по акту", "итого по акту"],
            Metric.AGENTS_PAID_AMOUNT.value: ["оплачено", "оплаты", "оплаченная сумма"],
            Metric.AGENTS_REMAINING_AMOUNT.value: ["остаток", "остаток к оплате", "осталось оплатить"],
            Metric.AGENTS_DDU_ASSIGNMENT_AMOUNT.value: ["дду плюс уступка", "дду+уступка"],
            Metric.AGENTS_DDU_AMOUNT.value: ["дду сумма", "сумма дду"],
            Metric.AGENTS_ASSIGNMENT_AMOUNT.value: ["уступка", "сумма уступки"],
            Metric.AGENTS_FURNITURE_AMOUNT.value: ["меблировка", "мебель"],
            Metric.AGENTS_MONTHLY_VALUE.value: ["помесячно", "график", "помесячная сумма"],
        },
        "metric_bundles": {
            "summary": {
                "aliases": ["итоги", "итог", "сводка", "отчет по агентам"],
                "metrics": [
                    Metric.AGENTS_DEAL_COUNT.value,
                    Metric.AGENTS_COMMISSION_AMOUNT.value,
                    Metric.AGENTS_PAID_AMOUNT.value,
                    Metric.AGENTS_REMAINING_AMOUNT.value,
                ],
            },
            "ddu": {
                "aliases": ["дду уступка", "дду и уступка", "дду меблировка"],
                "metrics": [
                    Metric.AGENTS_DDU_ASSIGNMENT_AMOUNT.value,
                    Metric.AGENTS_DDU_AMOUNT.value,
                    Metric.AGENTS_ASSIGNMENT_AMOUNT.value,
                    Metric.AGENTS_FURNITURE_AMOUNT.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.AGENTS_SUMMARY.value: {
                "aliases": ["отчет по агентам", "агенты", "сводка агентов", "агентские вознаграждения"],
                "meaning": "безопасная сводка отчета по агентам",
            },
            PaymentCalendarView.AGENTS_MONTHLY.value: {
                "aliases": ["помесячно", "по месяцам", "график", "график оплат"],
                "meaning": "помесячные графики ДДУ и уступки",
            },
            PaymentCalendarView.AGENTS_BY_BUDGET_MONTH.value: {
                "aliases": ["по бюджетным месяцам", "бюджетные месяцы", "по бюджету"],
                "meaning": "агрегаты по месяцу бюджета",
            },
            PaymentCalendarView.AGENTS_DDU.value: {
                "aliases": ["дду", "уступка", "меблировка", "дду и уступка"],
                "meaning": "суммы ДДУ, уступки и меблировки",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_SNAPSHOTS.value: {
                "aliases": ["какие срезы", "доступные срезы", "версии отчета"],
                "meaning": "список доступных срезов отчета по агентам",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_BUDGET_MONTHS.value: {
                "aliases": ["какие бюджетные месяцы", "месяцы бюджета"],
                "meaning": "список месяцев бюджета",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_PAYMENT_MONTHS.value: {
                "aliases": ["какие месяцы оплат", "месяцы графика", "периоды оплат"],
                "meaning": "список месяцев помесячных графиков",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_VALUE_KINDS.value: {
                "aliases": ["какие графики", "типы графиков", "дду уступка"],
                "meaning": "список типов помесячных графиков",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_AGENTS.value: {
                "aliases": ["какие агенты", "список агентов", "наименования агентов"],
                "meaning": "список наименований агентов",
            },
            PaymentCalendarView.AGENTS_AVAILABLE_UNIT_NUMBERS.value: {
                "aliases": ["номера помещений", "какие помещения", "список помещений"],
                "meaning": "список номеров помещений",
            },
        },
        "filters": {
            Dimension.VALUE_KIND.value: {
                "ddu_schedule": ["график дду", "дду"],
                "assignment_schedule": ["график уступки", "уступка"],
            },
            Dimension.PERIOD_KIND.value: {
                "past_periods_total": ["прошлые периоды"],
                "month": ["месяц", "помесячно"],
            },
        },
        "group_by": {
            GroupBy.BUDGET_MONTH.value: ["по бюджетным месяцам", "по бюджету"],
            GroupBy.PAYMENT_PERIOD_MONTH.value: ["по месяцам", "помесячно", "по месяцам оплат"],
            GroupBy.VALUE_KIND.value: ["по типам графиков", "дду и уступка"],
            GroupBy.AGENT.value: ["по агентам", "по наименованиям агентов"],
            GroupBy.UNIT_NUMBER.value: ["по помещениям", "по номерам помещений"],
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие срезы", "доступные срезы"],
            Dimension.BUDGET_MONTH.value: ["какие бюджетные месяцы", "месяцы бюджета"],
            Dimension.PAYMENT_PERIOD_MONTH.value: ["какие месяцы оплат", "периоды оплат"],
            Dimension.VALUE_KIND.value: ["какие графики", "типы графиков"],
            Dimension.AGENT.value: ["какие агенты", "список агентов", "наименования агентов"],
            Dimension.UNIT_NUMBER.value: ["номера помещений", "какие помещения", "список помещений"],
        },
    }
