from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.DEBT_ITEM_COUNT.value: ["количество", "сколько строк", "число строк", "количество записей"],
            Metric.DEBT_TOTAL_AMOUNT.value: ["сумма", "общая сумма", "сумма дз", "сумма броней", "итого"],
            Metric.DEBT_MONTHLY_VALUE.value: ["помесячно", "по месяцам", "месячные суммы", "график"],
            Metric.DEBT_PLAN_AMOUNT.value: ["план", "плановая сумма"],
            Metric.DEBT_UPDATED_PLAN_AMOUNT.value: ["уточненный план", "обновленный план", "актуальный план"],
            Metric.DEBT_FACT_PAYMENT_AMOUNT.value: ["факт оплат", "факт", "оплачено", "платежи факт"],
            Metric.DEBT_REMAINING_AMOUNT.value: ["остаток", "осталось", "разница", "отклонение"],
            Metric.DEBT_REFUSAL_COUNT.value: ["количество отказов", "отказы количество", "сколько отказов"],
            Metric.DEBT_REFUSAL_AREA.value: ["площадь отказов", "метры отказов", "площадь"],
            Metric.DEBT_REFUSAL_FULL_PRICE.value: ["сумма отказов", "стоимость отказов", "цена отказов"],
        },
        "metric_bundles": {
            "full": {
                "aliases": ["итоги", "итог", "сводка", "все показатели", "полный отчет"],
                "metrics": [Metric.DEBT_ITEM_COUNT.value, Metric.DEBT_TOTAL_AMOUNT.value],
            },
            "deviations": {
                "aliases": ["отклонения", "план факт", "план факт оплат"],
                "metrics": [
                    Metric.DEBT_PLAN_AMOUNT.value,
                    Metric.DEBT_UPDATED_PLAN_AMOUNT.value,
                    Metric.DEBT_FACT_PAYMENT_AMOUNT.value,
                    Metric.DEBT_REMAINING_AMOUNT.value,
                ],
            },
            "refusals": {
                "aliases": ["отказы", "отказы итоги"],
                "metrics": [
                    Metric.DEBT_REFUSAL_COUNT.value,
                    Metric.DEBT_REFUSAL_AREA.value,
                    Metric.DEBT_REFUSAL_FULL_PRICE.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.DEBT_BOOKINGS_SUMMARY.value: {
                "aliases": ["дз и брони", "дебиторка и брони", "сводка дз и броней", "итоги дз и броней"],
                "meaning": "сводка ДЗ и броней по безопасным агрегатам",
            },
            PaymentCalendarView.DEBT_BOOKINGS_MONTHLY.value: {
                "aliases": ["помесячно", "по месяцам", "график", "месячные суммы"],
                "meaning": "помесячные суммы ДЗ и броней",
            },
            PaymentCalendarView.DEBT_BOOKINGS_DEVIATIONS.value: {
                "aliases": ["отклонения", "план факт", "план факт оплат", "остаток по оплатам"],
                "meaning": "лист отклонений: план, уточненный план, факт оплат, остаток",
            },
            PaymentCalendarView.DEBT_BOOKINGS_REFUSALS.value: {
                "aliases": ["отказы", "отказники", "отказались"],
                "meaning": "агрегаты по отказам",
            },
            PaymentCalendarView.DEBT_BOOKINGS_BOOKINGS.value: {
                "aliases": ["брони", "бронирования"],
                "meaning": "строки броней",
            },
            PaymentCalendarView.DEBT_BOOKINGS_OVERDUE.value: {
                "aliases": ["просроченные", "просрочка", "просроченная дз"],
                "meaning": "просроченные строки",
            },
            PaymentCalendarView.DEBT_BOOKINGS_CURRENT.value: {
                "aliases": ["текущие", "текущая дз"],
                "meaning": "текущие строки",
            },
            PaymentCalendarView.DEBT_BOOKINGS_REGISTERED.value: {
                "aliases": ["зарегистрировано", "зарегистрированные"],
                "meaning": "зарегистрированные строки",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_PERIODS.value: {
                "aliases": ["какие периоды", "доступные периоды", "какие месяцы", "какие срезы"],
                "meaning": "список доступных срезов отчета ДЗ и брони",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_KINDS.value: {
                "aliases": ["какие типы", "типы строк", "какие разделы"],
                "meaning": "список типов строк ДЗ и броней",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_SECTIONS.value: {
                "aliases": ["какие разделы", "список разделов", "какие секции"],
                "meaning": "список разделов отчета",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_UNIT_NUMBERS.value: {
                "aliases": ["какие номера помещений", "номера помещений", "список помещений", "какие помещения"],
                "meaning": "список номеров помещений в отчете",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_STATUSES.value: {
                "aliases": ["какие статусы отказов", "статусы отказов", "статусы"],
                "meaning": "список статусов отказов",
            },
            PaymentCalendarView.DEBT_BOOKINGS_AVAILABLE_PAYMENT_TYPES.value: {
                "aliases": ["какие способы оплаты", "типы оплаты", "способы оплаты"],
                "meaning": "список способов оплаты по отказам",
            },
        },
        "filters": {
            Dimension.ITEM_KIND.value: {
                "total": ["итого", "всего"],
                "registered": ["зарегистрировано", "зарегистрированные"],
                "overdue": ["просроченные", "просрочка"],
                "current": ["текущие", "текущая дз"],
                "dupt_signed_unregistered": ["дупт подписан", "не зарегистрирован"],
                "booking": ["брони", "бронирования"],
                "refusal": ["отказы"],
            },
            Dimension.SECTION.value: {
                "type": "free_text_search",
                "examples": ["Просроченные", "Брони"],
            },
            Dimension.STATUS.value: {
                "type": "free_text_search",
                "examples": ["Отказ"],
            },
            Dimension.PAYMENT_TYPE.value: {
                "type": "free_text_search",
                "examples": ["ипотека", "100%"],
            },
        },
        "group_by": {
            GroupBy.ITEM_KIND.value: ["по типам", "по разделам", "в разрезе типов"],
            GroupBy.SECTION.value: ["по секциям", "по разделам отчета"],
            GroupBy.UNIT_NUMBER.value: ["по помещениям", "по номерам помещений", "в разрезе помещений"],
            GroupBy.MONTH.value: ["по месяцам", "помесячно"],
            GroupBy.STATUS.value: ["по статусам", "статусы"],
            GroupBy.PAYMENT_TYPE.value: ["по способам оплаты", "по типам оплаты"],
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие периоды", "доступные периоды", "какие срезы"],
            Dimension.ITEM_KIND.value: ["какие типы", "типы строк", "какие разделы"],
            Dimension.SECTION.value: ["какие секции", "список разделов"],
            Dimension.UNIT_NUMBER.value: ["какие номера помещений", "номера помещений", "список помещений"],
            Dimension.STATUS.value: ["какие статусы отказов", "статусы отказов"],
            Dimension.PAYMENT_TYPE.value: ["какие способы оплаты", "типы оплаты"],
        },
    }
