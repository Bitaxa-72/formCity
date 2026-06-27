from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.SALES_PLAN_REVENUE.value: ["продажи", "выручка", "продажи руб", "план продаж в деньгах"],
            Metric.SALES_PLAN_CASH_RECEIPTS.value: ["поступления", "поступление денежных средств", "дс", "денежные средства"],
            Metric.SALES_PLAN_CONTRACT_AREA_SQM.value: ["площадь", "квадратные метры", "м2", "объем площадей"],
            Metric.SALES_PLAN_CONTRACT_COUNT.value: ["сделки", "количество сделок", "штуки", "помещения"],
            Metric.SALES_PLAN_PRICE_PER_SQM.value: ["цена за метр", "цена м2", "цена за 1 м2"],
        },
        "metric_bundles": {
            "summary": {
                "aliases": ["итоги", "итог", "сводка", "исполнение плана продаж"],
                "metrics": [
                    Metric.SALES_PLAN_REVENUE.value,
                    Metric.SALES_PLAN_CASH_RECEIPTS.value,
                    Metric.SALES_PLAN_CONTRACT_AREA_SQM.value,
                    Metric.SALES_PLAN_CONTRACT_COUNT.value,
                ],
            },
            "segments": {
                "aliases": ["по сегментам", "по типам помещений", "разбивка"],
                "metrics": [
                    Metric.SALES_PLAN_REVENUE.value,
                    Metric.SALES_PLAN_CONTRACT_AREA_SQM.value,
                    Metric.SALES_PLAN_CONTRACT_COUNT.value,
                    Metric.SALES_PLAN_PRICE_PER_SQM.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.SALES_PLAN_SUMMARY.value: {
                "aliases": ["исполнение плана продаж", "план продаж", "выполнение плана продаж", "сводка исполнения плана"],
                "meaning": "верхний накопительный блок по итого проекта",
            },
            PaymentCalendarView.SALES_PLAN_BY_SEGMENTS.value: {
                "aliases": ["по сегментам", "по типам помещений", "разбивка по сегментам"],
                "meaning": "исполнение плана по сегментам",
            },
            PaymentCalendarView.SALES_PLAN_MONTH.value: {
                "aliases": ["месячный блок", "за месяц", "конкретный месяц"],
                "meaning": "блок конкретного месяца",
            },
            PaymentCalendarView.SALES_PLAN_YEAR.value: {
                "aliases": ["итого год", "за год", "итого 2026"],
                "meaning": "годовой блок исполнения плана",
            },
            PaymentCalendarView.SALES_PLAN_LIFETIME.value: {
                "aliases": ["весь проект", "итого проект", "общий итог"],
                "meaning": "общий итог проекта",
            },
            PaymentCalendarView.SALES_PLAN_PRICE_PER_SQM.value: {
                "aliases": ["цена за метр", "цена м2", "стоимость метра"],
                "meaning": "цена за м2 по сегментам",
            },
            PaymentCalendarView.SALES_PLAN_APARTMENTS.value: {
                "aliases": ["апартаменты", "апарты"],
                "meaning": "сегмент апартаментов",
            },
            PaymentCalendarView.SALES_PLAN_RESTAURANT.value: {
                "aliases": ["ресторан", "общепит"],
                "meaning": "сегмент ресторана",
            },
            PaymentCalendarView.SALES_PLAN_AVAILABLE_SNAPSHOTS.value: {
                "aliases": ["какие срезы", "доступные срезы", "версии отчета"],
                "meaning": "список доступных срезов исполнения плана продаж",
            },
            PaymentCalendarView.SALES_PLAN_AVAILABLE_SEGMENTS.value: {
                "aliases": ["какие сегменты", "сегменты", "типы помещений"],
                "meaning": "список сегментов исполнения плана",
            },
            PaymentCalendarView.SALES_PLAN_AVAILABLE_METRICS.value: {
                "aliases": ["какие показатели", "метрики", "что есть"],
                "meaning": "список показателей исполнения плана",
            },
            PaymentCalendarView.SALES_PLAN_AVAILABLE_SCENARIOS.value: {
                "aliases": ["какие сценарии", "план факт прогноз", "сценарии"],
                "meaning": "список сценариев исполнения плана",
            },
            PaymentCalendarView.SALES_PLAN_AVAILABLE_BLOCKS.value: {
                "aliases": ["какие блоки", "разделы отчета", "типы периодов"],
                "meaning": "список блоков отчета",
            },
        },
        "filters": {
            Dimension.SEGMENT.value: {
                "project_total": ["итого проект", "весь проект", "проект"],
                "apartments": ["апартаменты", "апарты"],
                "restaurant": ["ресторан", "общепит"],
            },
            Dimension.OWNER_SCOPE.value: {
                "all": ["все", "общий"],
                "developer": ["застройщик"],
                "well": ["велл"],
            },
            Dimension.SCENARIO.value: {
                "plan": ["план"],
                "fact": ["факт"],
                "deviation": ["отклонение"],
                "forecast": ["прогноз"],
                "fact_forecast": ["факт прогноз", "факт+прогноз"],
                "forecast_deviation": ["отклонение по прогнозу"],
                "fact_minus_forecast": ["разница факт прогноз"],
                "fact_actualized_forecast": ["факт актуализированный прогноз"],
                "remaining_to_sell": ["остаток к продаже"],
            },
            Dimension.PERIOD_KIND.value: {
                "snapshot": ["верхний блок", "накопительно"],
                "month": ["месячный блок", "месяц"],
                "year": ["год", "итого год"],
                "project_total": ["весь проект", "итого проект"],
            },
        },
        "group_by": {
            GroupBy.SEGMENT.value: ["по сегментам", "по типам помещений"],
            GroupBy.SCENARIO.value: ["план факт прогноз", "по сценариям"],
            GroupBy.OWNER_SCOPE.value: ["по владельцам", "застройщик и велл"],
            GroupBy.PERIOD_KIND.value: ["по блокам", "по типам периодов"],
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие срезы", "доступные срезы"],
            Dimension.SEGMENT.value: ["какие сегменты", "типы помещений"],
            Dimension.METRIC_KEY.value: ["какие показатели", "метрики"],
            Dimension.SCENARIO.value: ["какие сценарии", "план факт прогноз"],
            Dimension.PERIOD_KIND.value: ["какие блоки", "типы периодов"],
        },
    }
