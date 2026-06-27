from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


DEBT_AND_BOOKINGS_ALLOWED_GROUP_BY = {
    "month",
    "period",
    "period_month",
    "snapshot_month",
    "source_kind",
    "item_kind",
    "row_type",
    "section",
    "unit_number",
    "status",
    "payment_type",
}
DEBT_AND_BOOKINGS_HELP_MESSAGE = (
    "В отчете ДЗ и брони сейчас доступны:\n"
    "- количество строк\n"
    "- сумма по ДЗ и броням\n"
    "- помесячные суммы\n"
    "- отклонения: план, уточненный план, факт оплат, остаток\n"
    "- отказы: количество, площадь, сумма\n"
    "- разрезы по типам, разделам, номерам помещений, статусам, способам оплаты и периодам"
)
DEBT_AND_BOOKINGS_UNSUPPORTED_ALIASES = {
    "телефон": "контактные данные",
    "контакт": "контактные данные",
    "фио": "ФИО",
    "клиент": "клиенты",
    "покупател": "покупатели",
    "менеджер": "менеджеры",
    "коммент": "комментарии",
    "причин": "причины отказов",
    "паспорт": "паспортные данные",
    "документ": "номера документов",
}


def find_debt_and_bookings_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in DEBT_AND_BOOKINGS_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_debt_and_bookings_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in DEBT_AND_BOOKINGS_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_debt_and_bookings",
            message=DEBT_AND_BOOKINGS_HELP_MESSAGE,
        )

    unsupported_alias = find_debt_and_bookings_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_field_not_supported_for_debt_and_bookings",
            message=(
                f'В отчете ДЗ и брони не вывожу "{unsupported_alias}" по правилам безопасности.\n\n'
                f"{DEBT_AND_BOOKINGS_HELP_MESSAGE}"
            ),
        )

    return CompatibilityCheck(valid=True)
