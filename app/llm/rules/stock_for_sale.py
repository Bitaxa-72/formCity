from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
        "metrics": {
            Metric.STOCK_DDU_AMOUNT.value: ["дду", "сумма дду", "стоимость по дду"],
            Metric.STOCK_DUPT_MARKUP_AMOUNT.value: ["дупт", "наценка дупт", "наценка"],
            Metric.STOCK_TOTAL_AMOUNT.value: ["сумма", "общая сумма", "итого", "стоимость", "всего"],
            Metric.STOCK_AREA_SQM.value: ["площадь", "квадратные метры", "метры", "м2"],
            Metric.STOCK_UNIT_COUNT.value: ["количество", "штук", "объекты", "помещения", "сколько"],
            Metric.STOCK_DDU_PRICE_PER_SQM.value: ["цена дду за метр", "цена дду м2"],
            Metric.STOCK_DUPT_PRICE_PER_SQM.value: ["цена дупт за метр", "дупт за м2"],
            Metric.STOCK_TOTAL_PRICE_PER_SQM.value: ["цена за метр", "цена м2", "средняя цена", "стоимость метра"],
        },
        "metric_bundles": {
            "summary": {
                "aliases": ["итоги", "итог", "сводка", "остатки в продаже", "экспозиция"],
                "metrics": [
                    Metric.STOCK_TOTAL_AMOUNT.value,
                    Metric.STOCK_AREA_SQM.value,
                    Metric.STOCK_UNIT_COUNT.value,
                    Metric.STOCK_TOTAL_PRICE_PER_SQM.value,
                ],
            },
            "amounts": {
                "aliases": ["суммы", "дду и дупт", "стоимость дду дупт"],
                "metrics": [
                    Metric.STOCK_DDU_AMOUNT.value,
                    Metric.STOCK_DUPT_MARKUP_AMOUNT.value,
                    Metric.STOCK_TOTAL_AMOUNT.value,
                ],
            },
            "prices": {
                "aliases": ["цены", "цена за метр", "цены за м2"],
                "metrics": [
                    Metric.STOCK_DDU_PRICE_PER_SQM.value,
                    Metric.STOCK_DUPT_PRICE_PER_SQM.value,
                    Metric.STOCK_TOTAL_PRICE_PER_SQM.value,
                ],
            },
        },
        "views": {
            PaymentCalendarView.STOCK_SUMMARY.value: {
                "aliases": ["остатки в продаже", "экспозиция", "сводка остатков", "итоги остатков"],
                "meaning": "строка Всего по остаткам в продаже",
            },
            PaymentCalendarView.STOCK_AMOUNTS.value: {
                "aliases": ["суммы", "дду и дупт", "стоимость"],
                "meaning": "суммы ДДУ, наценки ДУПТ и итого",
            },
            PaymentCalendarView.STOCK_PRICE_PER_SQM.value: {
                "aliases": ["цена за метр", "цена м2", "цены за м2", "стоимость метра"],
                "meaning": "цены за м2",
            },
            PaymentCalendarView.STOCK_BY_FLOORS.value: {
                "aliases": ["по этажам", "разбивка по этажам", "этажи"],
                "meaning": "детализация остатков по этажам",
            },
            PaymentCalendarView.STOCK_IN_WORK.value: {
                "aliases": ["в работе", "объекты в работе", "помещения в работе"],
                "meaning": "строки остатков, отмеченные как в работе",
            },
            PaymentCalendarView.STOCK_DETAILS.value: {
                "aliases": ["детально", "подробно", "по строкам", "детализация"],
                "meaning": "детальные строки отчета остатков",
            },
            PaymentCalendarView.STOCK_APARTMENTS.value: {
                "aliases": ["апартаменты", "апарты"],
                "meaning": "категория апартаментов",
            },
            PaymentCalendarView.STOCK_STORAGE.value: {
                "aliases": ["кладовые", "кладовки"],
                "meaning": "категория кладовых",
            },
            PaymentCalendarView.STOCK_RESTAURANTS.value: {
                "aliases": ["рестораны", "общепит"],
                "meaning": "категория ресторанов",
            },
            PaymentCalendarView.STOCK_FIRST_FLOOR.value: {
                "aliases": ["первый этаж", "1 этаж"],
                "meaning": "объекты первого этажа",
            },
            PaymentCalendarView.STOCK_DEVELOPER_BALANCE.value: {
                "aliases": ["остаток застройщика", "баланс застройщика"],
                "meaning": "объекты на балансе застройщика",
            },
            PaymentCalendarView.STOCK_AVAILABLE_PERIODS.value: {
                "aliases": ["какие периоды", "доступные периоды", "какие месяцы", "какие срезы"],
                "meaning": "список доступных срезов остатков",
            },
            PaymentCalendarView.STOCK_AVAILABLE_PROPERTY_TYPES.value: {
                "aliases": ["какие типы объектов", "типы объектов", "какие категории"],
                "meaning": "список типов объектов в остатках",
            },
            PaymentCalendarView.STOCK_AVAILABLE_ROW_TYPES.value: {
                "aliases": ["какие виды строк", "виды строк"],
                "meaning": "список видов строк отчета",
            },
            PaymentCalendarView.STOCK_AVAILABLE_FLOORS.value: {
                "aliases": ["какие этажи", "список этажей", "этажи есть"],
                "meaning": "список этажей в остатках",
            },
        },
        "filters": {
            Dimension.PROPERTY_TYPE.value: {
                "apartment": ["апартаменты", "апарты"],
                "storage": ["кладовые", "кладовки"],
                "restaurant": ["рестораны", "общепит"],
                "first_floor": ["первый этаж", "1 этаж"],
                "developer_balance": ["остаток застройщика", "баланс застройщика"],
                "total": ["всего", "итого"],
            },
            Dimension.ROW_LABEL.value: {
                "type": "free_text_search",
                "examples": ["1 этаж", "апартаменты", "СЗ обв"],
            },
        },
        "group_by": {
            GroupBy.PROPERTY_TYPE.value: ["по типам объектов", "по категориям"],
            GroupBy.FLOOR_NUMBER.value: ["по этажам", "в разрезе этажей"],
            GroupBy.ROW_LABEL.value: ["по строкам", "детально"],
            GroupBy.MONTH.value: ["по месяцам", "по срезам"],
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие периоды", "доступные периоды", "какие срезы"],
            Dimension.PROPERTY_TYPE.value: ["какие типы объектов", "типы объектов", "какие категории"],
            Dimension.ROW_TYPE.value: ["какие виды строк", "виды строк"],
            Dimension.FLOOR_NUMBER.value: ["какие этажи", "список этажей"],
        },
    }
