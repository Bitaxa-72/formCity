from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


SALES_REPORT_ALLOWED_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "period_month",
    "segment",
    "metric_key",
    "owner_scope",
    "period_kind",
    "scenario",
}
SALES_REPORT_HELP_MESSAGE = (
    "В отчете о продажах сейчас доступны:\n"
    "- выручка по контрактации\n"
    "- объем контрактации в м2\n"
    "- количество сделок / помещений\n"
    "- цена за м2\n"
    "- фактические оплаты по ДДУ\n"
    "- график оплаты остатка по ДДУ\n"
    "- разрезы по сегментам, месяцам продаж, сценариям и владельцу"
)
SALES_REPORT_UNSUPPORTED_ALIASES = {
    "покупател": "покупатели",
    "клиент": "клиенты",
    "фио": "ФИО",
    "телефон": "контактные данные",
    "контакт": "контактные данные",
    "паспорт": "паспортные данные",
    "документ": "номера документов",
    "договор": "договоры",
}


def find_sales_report_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in SALES_REPORT_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_sales_report_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in SALES_REPORT_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_sales_report",
            message=SALES_REPORT_HELP_MESSAGE,
        )

    unsupported_alias = find_sales_report_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_field_not_supported_for_sales_report",
            message=(
                f'В отчете о продажах не вывожу "{unsupported_alias}" по правилам безопасности.\n\n'
                f"{SALES_REPORT_HELP_MESSAGE}"
            ),
        )

    return CompatibilityCheck(valid=True)
