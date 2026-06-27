from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.SALES_CONTRACT_REVENUE.value: ["выручка", "выручка по контрактации", "контрактация в деньгах"],
            Metric.SALES_CONTRACT_AREA_SQM.value: ["квадратные метры", "площадь", "объем контрактации м2", "метры"],
            Metric.SALES_CONTRACT_COUNT.value: ["сделки", "количество сделок", "помещения", "штуки"],
            Metric.SALES_PRICE_PER_SQM.value: ["цена за метр", "цена м2", "цена за 1 кв.м."],
            Metric.SALES_DDU_ACTUAL_PAYMENTS.value: ["фактические оплаты по дду", "оплаты дду", "факт оплат"],
            Metric.SALES_DDU_REMAINING_PAYMENT_SCHEDULE.value: ["график оплаты остатка по дду", "остаток по дду", "остаток оплат"],
            Metric.SALES_CUMULATIVE_PRICE_PER_SQM.value: ["накопительная цена", "накопительная цена за метр"],
        },
        "metric_bundles": {
            "summary": {
                "aliases": ["итоги", "итог", "сводка", "отчет о продажах"],
                "metrics": [
                    Metric.SALES_CONTRACT_REVENUE.value,
                    Metric.SALES_DDU_ACTUAL_PAYMENTS.value,
                    Metric.SALES_DDU_REMAINING_PAYMENT_SCHEDULE.value,
                ],
            },
            "segments": {
                "aliases": ["по сегментам", "по типам помещений", "разбивка"],
                "metrics": [
                    Metric.SALES_CONTRACT_REVENUE.value,
                    Metric.SALES_CONTRACT_AREA_SQM.value,
                    Metric.SALES_CONTRACT_COUNT.value,
                    Metric.SALES_PRICE_PER_SQM.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.SALES_SUMMARY.value: {
                "aliases": ["отчет о продажах", "продажи", "сводка продаж", "итоги продаж"],
                "meaning": "сводка продаж по project_total",
            },
            PaymentCalendarView.SALES_BY_SEGMENTS.value: {
                "aliases": ["по сегментам", "по типам помещений", "разбивка по сегментам"],
                "meaning": "продажи по сегментам",
            },
            PaymentCalendarView.SALES_MONTHLY.value: {
                "aliases": ["помесячно", "по месяцам", "динамика продаж"],
                "meaning": "помесячные значения продаж",
            },
            PaymentCalendarView.SALES_PAYMENTS.value: {
                "aliases": ["оплаты", "оплаты по ДДУ", "фактические оплаты", "остаток по ДДУ"],
                "meaning": "фактические оплаты и график оплаты остатка по ДДУ",
            },
            PaymentCalendarView.SALES_PRICE_PER_SQM.value: {
                "aliases": ["цена за метр", "цены за м2", "стоимость метра"],
                "meaning": "цены за м2 по сегментам",
            },
            PaymentCalendarView.SALES_APARTMENTS.value: {
                "aliases": ["апартаменты", "апарты"],
                "meaning": "сегмент апартаментов",
            },
            PaymentCalendarView.SALES_COMMERCIAL_1_FLOOR.value: {
                "aliases": ["коммерция 1 этаж", "первый этаж"],
                "meaning": "сегмент коммерции 1 этаж",
            },
            PaymentCalendarView.SALES_RESTAURANT.value: {
                "aliases": ["ресторан", "общепит"],
                "meaning": "сегмент ресторана",
            },
            PaymentCalendarView.SALES_STORAGE.value: {
                "aliases": ["кладовки", "кладовые"],
                "meaning": "сегмент кладовок",
            },
            PaymentCalendarView.SALES_COMMERCIAL_2_FLOOR.value: {
                "aliases": ["коммерция 2 этаж", "второй этаж"],
                "meaning": "сегмент коммерции 2 этаж",
            },
            PaymentCalendarView.SALES_SH.value: {
                "aliases": ["sh"],
                "meaning": "сегмент SH",
            },
            PaymentCalendarView.SALES_AVAILABLE_SNAPSHOTS.value: {
                "aliases": ["какие срезы", "доступные срезы", "версии отчета"],
                "meaning": "список доступных срезов отчета о продажах",
            },
            PaymentCalendarView.SALES_AVAILABLE_PERIODS.value: {
                "aliases": ["какие месяцы", "периоды продаж", "доступные периоды"],
                "meaning": "список месяцев продаж внутри отчета",
            },
            PaymentCalendarView.SALES_AVAILABLE_SEGMENTS.value: {
                "aliases": ["какие сегменты", "сегменты", "типы помещений"],
                "meaning": "список сегментов продаж",
            },
            PaymentCalendarView.SALES_AVAILABLE_METRICS.value: {
                "aliases": ["какие показатели", "метрики продаж", "что есть"],
                "meaning": "список показателей отчета продаж",
            },
            PaymentCalendarView.SALES_AVAILABLE_OWNERS.value: {
                "aliases": ["какие владельцы", "застройщик велл", "owner scope"],
                "meaning": "список владельцев",
            },
            PaymentCalendarView.SALES_AVAILABLE_SCENARIOS.value: {
                "aliases": ["какие сценарии", "план факт", "сценарии"],
                "meaning": "список сценариев",
            },
        },
        "filters": {
            Dimension.SEGMENT.value: {
                "project_total": ["итого по проекту", "весь проект"],
                "apartments": ["апартаменты", "апарты"],
                "commercial_1_floor": ["коммерция 1 этаж", "первый этаж"],
                "restaurant": ["ресторан", "общепит"],
                "storage": ["кладовки", "кладовые"],
                "commercial_2_floor": ["коммерция 2 этаж", "второй этаж"],
                "sh": ["sh"],
            },
            Dimension.SCENARIO.value: {
                "fact": ["факт", "фактический"],
                "plan": ["план", "плановый"],
                "total": ["итого"],
            },
            Dimension.OWNER_SCOPE.value: {
                "all": ["все", "общий"],
                "developer": ["застройщик"],
                "well": ["велл"],
                "well_including": ["в том числе велл"],
            },
        },
        "group_by": {
            GroupBy.SEGMENT.value: ["по сегментам", "по типам помещений"],
            GroupBy.PERIOD_MONTH.value: ["по месяцам", "помесячно"],
            GroupBy.SCENARIO.value: ["план факт", "по сценариям"],
            GroupBy.OWNER_SCOPE.value: ["по владельцам", "застройщик и велл"],
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие срезы", "доступные срезы"],
            Dimension.PERIOD_MONTH.value: ["какие месяцы", "периоды продаж"],
            Dimension.SEGMENT.value: ["какие сегменты", "типы помещений"],
            Dimension.METRIC_KEY.value: ["какие показатели", "метрики продаж"],
            Dimension.OWNER_SCOPE.value: ["какие владельцы"],
            Dimension.SCENARIO.value: ["какие сценарии", "план факт"],
        },
    }
