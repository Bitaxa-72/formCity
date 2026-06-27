from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
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
    }
