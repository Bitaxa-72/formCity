from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


AGENTS_REPORT_ALLOWED_GROUP_BY = {
    "month",
    "period",
    "snapshot_month",
    "source_kind",
    "agent",
    "unit_number",
    "budget_month",
    "period_month",
    "payment_period_month",
    "value_kind",
    "period_kind",
}
AGENTS_REPORT_HELP_MESSAGE = (
    "В отчете по агентам доступны безопасные агрегаты:\n"
    "- количество сделок\n"
    "- площадь\n"
    "- база вознаграждения\n"
    "- агентское вознаграждение\n"
    "- сумма по акту\n"
    "- оплачено\n"
    "- остаток к оплате\n"
    "- суммы ДДУ, уступки и меблировки\n"
    "- помесячные графики ДДУ и уступки\n"
    "- разрезы по наименованию агента и номерам помещений"
)
AGENTS_REPORT_UNSUPPORTED_ALIASES = {
    "покупател": "покупатели",
    "клиент": "клиенты",
    "фио": "ФИО",
    "телефон": "контактные данные",
    "контакт": "контактные данные",
    "номер дду": "номера ДДУ",
    "номера дду": "номера ДДУ",
    "дду номер": "номера ДДУ",
    "номер акта": "номера и даты актов",
    "номера актов": "номера и даты актов",
    "дата акта": "номера и даты актов",
    "документ": "номера документов",
    "примеч": "примечания",
}


def find_agents_report_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in AGENTS_REPORT_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_agents_report_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in AGENTS_REPORT_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_agents_report",
            message=AGENTS_REPORT_HELP_MESSAGE,
        )

    unsupported_alias = find_agents_report_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_field_not_supported_for_agents_report",
            message=(
                f'В отчете по агентам не вывожу "{unsupported_alias}" по правилам безопасности.\n\n'
                f"{AGENTS_REPORT_HELP_MESSAGE}"
            ),
        )

    return CompatibilityCheck(valid=True)
