from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


MODEL_ALLOWED_GROUP_BY = {"month", "metric", "snapshot_month"}
MODEL_UNSUPPORTED_ALIASES = {
    "этаж": "этажность",
    "дду": "ДДУ",
    "паспорт": "паспортные или документные данные",
    "телефон": "контакты",
    "контакт": "контакты",
    "документ": "номера документов",
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
    "Также можно спросить: доступные показатели модели или доступные срезы модели."
)


def find_model_unsupported_alias(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    for alias, label in MODEL_UNSUPPORTED_ALIASES.items():
        if alias in normalized:
            return label
    return None


def check_model_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
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

    return CompatibilityCheck(valid=True)
