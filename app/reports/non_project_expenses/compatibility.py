from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


NON_PROJECT_EXPENSES_ALLOWED_GROUP_BY = {"period", "month", "item_kind", "fm_category", "item_name", "row_type"}
NON_PROJECT_EXPENSES_HELP_MESSAGE = (
    "В непроектных расходах сейчас доступны:\n"
    "- сумма\n"
    "- исполнено\n"
    "- остаток / прогноз\n"
    "- категории\n"
    "- строки\n"
    "- типы строк\n"
    "- доступные периоды"
)
NON_PROJECT_EXPENSES_UNSUPPORTED_ALIASES = {
    "выручк": "выручка",
    "сделк": "количество сделок",
    "квадрат": "площадь",
    "цена метр": "цена метра",
    "этаж": "этажи",
    "помещен": "помещения",
    "телефон": "контактные данные",
    "контакт": "контактные данные",
    "паспорт": "паспортные данные",
    "документ": "номера документов",
}


def find_non_project_expenses_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in NON_PROJECT_EXPENSES_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_non_project_expenses_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in NON_PROJECT_EXPENSES_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_non_project_expenses",
            message=NON_PROJECT_EXPENSES_HELP_MESSAGE,
        )

    unsupported_alias = find_non_project_expenses_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="metric_not_supported_for_non_project_expenses",
            message=f'В непроектных расходах нет показателя "{unsupported_alias}".\n\n{NON_PROJECT_EXPENSES_HELP_MESSAGE}',
        )

    return CompatibilityCheck(valid=True)
