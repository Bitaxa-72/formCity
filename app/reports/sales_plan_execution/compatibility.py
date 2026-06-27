from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


SALES_PLAN_EXECUTION_UNSUPPORTED_METRIC_ALIASES = {
    "агент": "агентские данные",
    "агентское": "агентские данные",
    "реклама": "реклама",
    "фот": "ФОТ",
    "долг": "долги",
    "бронь": "брони",
}

SALES_PLAN_EXECUTION_HELP = (
    "В отчете об исполнении плана продаж доступны агрегаты по Обводному: "
    "продажи, поступления денежных средств, площадь контрактации, количество сделок и цена за м2. "
    "Можно смотреть план, факт, прогноз, отклонения, остаток к продаже, сегменты, доступные срезы и сценарии."
)


def normalize_text(value: str | None) -> str:
    return (value or "").casefold().replace("ё", "е")


def check_sales_plan_execution_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    if frame.report_type != "sales_plan_execution":
        return CompatibilityCheck(valid=True)

    normalized = normalize_text(user_text)
    for marker, label in SALES_PLAN_EXECUTION_UNSUPPORTED_METRIC_ALIASES.items():
        if marker in normalized:
            return CompatibilityCheck(
                valid=False,
                error="metric_not_supported_for_sales_plan_execution",
                message=f"В отчете об исполнении плана продаж нет показателя \"{label}\".\n\n{SALES_PLAN_EXECUTION_HELP}",
            )

    unsupported_group_by = set(frame.group_by) - {
        "snapshot_month",
        "period_month",
        "period",
        "month",
        "block_kind",
        "segment",
        "metric_key",
        "owner_scope",
        "period_kind",
        "scenario",
        "year",
    }
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_sales_plan_execution",
            message=SALES_PLAN_EXECUTION_HELP,
        )

    return CompatibilityCheck(valid=True)
