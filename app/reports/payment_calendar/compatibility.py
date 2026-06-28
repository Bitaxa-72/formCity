from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES = {
    "выручка": "выручка",
    "доход": "выручка",
    "продажи": "продажи",
    "сделки": "количество сделок",
    "сделок": "количество сделок",
    "количество сделок": "количество сделок",
    "цена метра": "цена метра",
    "цена квадратного метра": "цена метра",
    "средняя цена": "средняя цена",
    "квадраты": "квадратные метры",
    "площадь": "площадь",
    "метры": "квадратные метры",
    "квадратные метры": "квадратные метры",
    "npv": "NPV",
    "roe": "ROE",
    "llcr": "LLCR",
}
PAYMENT_CALENDAR_UNSUPPORTED_METRIC_REPORT_HINTS = {
    "выручка": "модель, отчет о продажах, исполнение плана продаж, сводный отчет",
    "продажи": "отчет о продажах, исполнение плана продаж, сводный отчет",
    "количество сделок": "отчет о продажах, отчет по агентам, исполнение плана продаж",
    "цена метра": "остатки в продаже, отчет о продажах, исполнение плана продаж",
    "средняя цена": "остатки в продаже, отчет о продажах, исполнение плана продаж",
    "квадратные метры": "модель, остатки в продаже, отчет о продажах, исполнение плана продаж",
    "площадь": "модель, остатки в продаже, отчет о продажах, исполнение плана продаж",
    "NPV": "модель",
    "ROE": "модель",
    "LLCR": "модель",
}

PAYMENT_CALENDAR_COMPATIBILITY_MESSAGE_TEMPLATE = (
    'В платежном календаре нет показателя "{metric}".\n\n'
    "Сейчас для платежного календаря доступны:\n"
    "- план\n"
    "- факт\n"
    "- отклонение\n"
    "- итоги\n"
    "- поступления\n"
    "- платежи\n"
    "- остатки\n"
    "- статьи расходов"
)
PAYMENT_CALENDAR_ALLOWED_GROUP_BY = {"project", "period", "month", "metric", "article", "article_kind"}
PAYMENT_CALENDAR_GROUP_BY_LABELS = {
    "floor": "этажам",
    "room_type": "типам помещений",
    "agent": "агентам",
    "bank": "банкам",
    "project": "проектам",
    "period": "периодам",
    "month": "месяцам",
    "metric": "показателям",
    "article": "статьям",
    "article_kind": "разделам",
}
PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE = (
    "В платежном календаре нет разбивки по {group_by}.\n\n"
    "Для платежного календаря доступны разбивки:\n"
    "- по проектам\n"
    "- по периодам\n"
    "- по статьям\n"
    "- по разделам: поступления, платежи, остатки, статьи расходов"
)


def build_payment_calendar_compatibility_message(metric: str) -> str:
    message = PAYMENT_CALENDAR_COMPATIBILITY_MESSAGE_TEMPLATE.format(metric=metric)
    report_hint = PAYMENT_CALENDAR_UNSUPPORTED_METRIC_REPORT_HINTS.get(metric)
    if report_hint:
        message += f"\n\nВозможно, показатель относится к другому отчету: {report_hint}."
    else:
        message += "\n\nЕсли нужен другой отчет, укажите его название."
    return message


def find_payment_calendar_unsupported_metric(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    if not normalized:
        return None

    for alias, label in PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES.items():
        if alias in normalized:
            return label
    return None


def find_payment_calendar_unsupported_group_by(frame: QueryFrame) -> str | None:
    for group_by in frame.group_by:
        if group_by not in PAYMENT_CALENDAR_ALLOWED_GROUP_BY:
            return PAYMENT_CALENDAR_GROUP_BY_LABELS.get(group_by, group_by)
    return None


def check_payment_calendar_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = find_payment_calendar_unsupported_group_by(frame)
    if unsupported_group_by is not None:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_payment_calendar",
            message=PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE.format(group_by=unsupported_group_by),
        )

    unsupported_metric = find_payment_calendar_unsupported_metric(user_text)
    if unsupported_metric is None:
        return CompatibilityCheck(valid=True)

    return CompatibilityCheck(
        valid=False,
        error="metric_not_supported_for_payment_calendar",
        message=build_payment_calendar_compatibility_message(unsupported_metric),
    )
