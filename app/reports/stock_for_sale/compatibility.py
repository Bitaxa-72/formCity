from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


STOCK_FOR_SALE_ALLOWED_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "row_type",
    "row_label",
    "property_type",
    "floor_number",
    "is_in_work",
}
STOCK_FOR_SALE_HELP_MESSAGE = (
    "В остатках в продаже сейчас доступны:\n"
    "- сумма ДДУ\n"
    "- наценка ДУПТ\n"
    "- сумма всего\n"
    "- площадь\n"
    "- количество объектов\n"
    "- цены за м2\n"
    "- разрезы по типам объектов, этажам и строкам в работе"
)
STOCK_FOR_SALE_UNSUPPORTED_ALIASES = {
    "покупател": "покупатели",
    "клиент": "клиенты",
    "фио": "ФИО",
    "телефон": "контактные данные",
    "контакт": "контактные данные",
    "паспорт": "паспортные данные",
    "документ": "номера документов",
    "договор": "договоры",
}


def find_stock_for_sale_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in STOCK_FOR_SALE_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_stock_for_sale_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in STOCK_FOR_SALE_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_stock_for_sale",
            message=STOCK_FOR_SALE_HELP_MESSAGE,
        )

    unsupported_alias = find_stock_for_sale_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_field_not_supported_for_stock_for_sale",
            message=(
                f'В остатках в продаже не вывожу "{unsupported_alias}" по правилам безопасности.\n\n'
                f"{STOCK_FOR_SALE_HELP_MESSAGE}"
            ),
        )

    return CompatibilityCheck(valid=True)
