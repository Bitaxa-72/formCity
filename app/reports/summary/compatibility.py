from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


SUMMARY_ALLOWED_GROUP_BY = {
    "project",
    "source_file",
    "sheet_name",
    "sheet_kind",
    "row_type",
    "header_key",
}
SUMMARY_HELP_MESSAGE = (
    "В сводном отчете сейчас доступны только безопасные агрегаты:\n"
    "- количество файлов, листов, строк и ячеек\n"
    "- список проектов, файлов, листов, типов листов и безопасных колонок\n"
    "- суммы по безопасным числовым колонкам\n\n"
    "Персональные строки, ФИО, номера договоров, ДДУ, ДКП, брони, контакты и примечания не выводятся."
)
SUMMARY_UNSUPPORTED_ALIASES = {
    "фио": "ФИО",
    "клиент": "клиенты",
    "покупател": "покупатели",
    "контакт": "контакты",
    "телефон": "телефоны",
    "менеджер": "менеджеры",
    "список агентов": "список агентов",
    "имена агентов": "имена агентов",
    "номер дду": "номера ДДУ",
    "номера дду": "номера ДДУ",
    "дду": "ДДУ",
    "дкп": "ДКП",
    "договор": "договоры",
    "бронь": "брони",
    "примеч": "примечания",
    "паспорт": "паспортные данные",
    "реквизит": "реквизиты",
}


def find_summary_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in SUMMARY_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_summary_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in SUMMARY_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_summary",
            message=SUMMARY_HELP_MESSAGE,
        )

    unsupported_alias = find_summary_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_field_not_supported_for_summary",
            message=(
                f'В сводном отчете не вывожу "{unsupported_alias}" по правилам безопасности.\n\n'
                f"{SUMMARY_HELP_MESSAGE}"
            ),
        )

    return CompatibilityCheck(valid=True)
