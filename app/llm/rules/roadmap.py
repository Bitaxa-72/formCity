from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView


RULE: dict[str, object] = {
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
    }
