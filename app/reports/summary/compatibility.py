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
    "В сводном отчете доступны безопасные данные из сводных таблиц:\n"
    "- количество файлов, листов, строк и ячеек\n"
    "- список проектов, файлов, листов, типов листов и безопасных колонок\n"
    "- суммы по безопасным числовым колонкам\n"
    "- разрезы по проектам, файлам, листам, типам листов, строкам и колонкам\n\n"
    "Не выводятся только персональные и документные поля из закрытого списка: ФИО клиента, телефоны, менеджер, примечания, номера договоров, ДДУ, регистраций, реестров, ПП, расписок МФЦ и ПИБ."
)
SUMMARY_UNSUPPORTED_ALIASES = {
    "фио клиента": "ФИО клиента",
    "фио клиентов": "ФИО клиента",
    "фио агента": "ФИО агента",
    "контакт": "контакты",
    "телефон": "телефоны",
    "менеджер": "менеджер",
    "номер договора брони": "номер договора брони",
    "номер договора уступки": "номер договора уступки",
    "номер дду": "номер ДДУ",
    "номера дду": "номера ДДУ",
    "№ дду": "№ ДДУ",
    "номер регистрации": "номер регистрации",
    "№ регистрации": "№ регистрации",
    "дата и № реестра": "Дата и № реестра",
    "№ пп": "№ ПП",
    "№ расписки": "№ расписки МФЦ",
    "№ пиб": "№ ПИБ",
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
