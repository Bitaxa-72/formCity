from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


MODEL_ALLOWED_GROUP_BY = {"month", "metric", "snapshot_month"}
MODEL_SENSITIVE_ALIASES = {
    "телефон": "телефоны",
    "телефоны": "телефоны",
    "номер телефона": "телефоны",
    "контакт": "контакты",
    "контакты": "контакты",
    "паспорт": "паспортные данные",
    "паспортные": "паспортные данные",
    "паспортные данные": "паспортные данные",
    "документ": "номера документов",
    "документы": "номера документов",
    "номер документа": "номера документов",
    "номера документов": "номера документов",
    "договор": "договоры",
    "договоры": "договоры",
    "дду": "номера договоров",
    "реквизит": "реквизиты",
    "реквизиты": "реквизиты",
    "фио": "персональные данные",
}
MODEL_UNSUPPORTED_ALIASES = {
    "этаж": "этажность",
    "план": "план",
    "факт": "факт",
    "отклон": "отклонение",
    "реклам": "реклама",
    "фот": "ФОТ",
    "сделк": "количество сделок",
    "количество сделок": "количество сделок",
    "цена метр": "цена метра",
    "цена метра": "цена метра",
    "цену метра": "цена метра",
    "стоимость метр": "цена метра",
    "стоимость метра": "цена метра",
}

MODEL_HELP_MESSAGE = (
    "В модели пока подключен верхнеуровневый слой KPI.\n\n"
    "Можно запросить:\n"
    "- выручку\n"
    "- себестоимость продаж\n"
    "- валовую прибыль\n"
    "- чистую прибыль\n"
    "- NPV\n"
    "- ROE\n"
    "- LLCR\n"
    "- общую площадь\n"
    "- количество помещений\n"
    "- ПИР\n\n"
    "Также можно спросить: доступные показатели модели, доступные срезы модели, raw-листы модели или строки листов Финмодель, Остатки, Для консолидации."
)
MODEL_SENSITIVE_MESSAGE = (
    "Эти данные не выводятся ботом по правилам безопасности.\n\n"
    "Я не показываю контакты, телефоны, паспортные данные, номера документов, договоров и реквизиты.\n\n"
    "По модели можно запросить KPI, доступные срезы и загруженные листы без персональных и документных данных."
)
MODEL_UNKNOWN_METRIC_MARKERS = {
    "показател",
    "метрик",
}
MODEL_UNKNOWN_METRIC_EXCLUSIONS = {
    "какие",
    "доступные",
    "список",
    "основные",
    "кратк",
    "свод",
    "итог",
}


def find_model_sensitive_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in MODEL_SENSITIVE_ALIASES.items():
        if alias in normalized:
            return label
    return None


def find_model_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in MODEL_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def is_model_unknown_metric_request(text: str | None) -> bool:
    normalized = normalize_search_text(text or "")
    if "модел" not in normalized:
        return False
    if not any(marker in normalized for marker in MODEL_UNKNOWN_METRIC_MARKERS):
        return False
    return not any(marker in normalized for marker in MODEL_UNKNOWN_METRIC_EXCLUSIONS)


def check_model_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    sensitive_alias = find_model_sensitive_alias(user_text)
    if sensitive_alias:
        return CompatibilityCheck(
            valid=False,
            error="sensitive_data_blocked_for_model",
            message=MODEL_SENSITIVE_MESSAGE,
        )

    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in MODEL_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_model",
            message=MODEL_HELP_MESSAGE,
        )

    unsupported_alias = find_model_unsupported_alias(user_text)
    if unsupported_alias:
        return CompatibilityCheck(
            valid=False,
            error="metric_not_supported_for_model",
            message=f'Показатель "{unsupported_alias}" сейчас не выводится из модели.\n\n{MODEL_HELP_MESSAGE}',
        )

    if is_model_unknown_metric_request(user_text):
        return CompatibilityCheck(
            valid=False,
            error="unknown_metric_for_model",
            message=f"Не нашел такой показатель в модели.\n\n{MODEL_HELP_MESSAGE}",
        )

    return CompatibilityCheck(valid=True)
