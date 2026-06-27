from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
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
                "aliases": [
                    "модель",
                    "финансовая модель",
                    "краткая модель",
                    "краткая сводка модели",
                    "сводка модели",
                    "итоги модели",
                    "основные показатели модели",
                ],
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
            PaymentCalendarView.MODEL_RAW_SHEETS.value: {
                "aliases": ["какие листы", "список листов", "листы модели", "какие таблицы есть в модели"],
                "meaning": "список raw-листов модели",
            },
            PaymentCalendarView.MODEL_RAW_ROWS.value: {
                "aliases": [
                    "фм",
                    "фм план",
                    "newkpi",
                    "newkpi план",
                    "паспорт",
                    "проценты",
                    "сравнение",
                    "финмодель",
                    "лист финмодель",
                    "остатки",
                    "лист остатки",
                    "для консолидации",
                    "лист для консолидации",
                ],
                "meaning": "строки выбранного raw-листа модели",
            },
            PaymentCalendarView.MODEL_RAW_SEARCH.value: {
                "aliases": ["найди в модели", "поиск в модели", "найди в финмодели", "найди в остатках"],
                "meaning": "поиск по безопасным raw-строкам модели",
            },
        },
        "dimensions": {
            Dimension.SNAPSHOT_MONTH.value: ["какие срезы", "доступные срезы", "какие версии модели"],
            Dimension.METRIC.value: ["какие показатели", "список показателей", "доступные показатели"],
            Dimension.RAW_SHEET.value: ["какие листы", "список листов", "какие таблицы есть в модели"],
        },
        "group_by": {
            GroupBy.MONTH.value: ["по срезам", "по месяцам модели", "по версиям модели"],
            GroupBy.METRIC.value: ["по показателям", "все показатели"],
        },
    }
