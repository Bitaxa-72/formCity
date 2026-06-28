from app.pipeline.domain_resolver import normalize_search_text
from app.pipeline.query_frame import QueryFrame
from app.reports.common import CompatibilityCheck


ROADMAP_UNSUPPORTED_METRIC_ALIASES = {
    "план": "план",
    "факт": "факт",
    "отклонение": "отклонение",
    "выручка": "выручка",
    "сделки": "количество сделок",
    "квадрат": "площадь",
    "метр": "площадь",
    "расход": "расходы",
    "поступлен": "поступления",
    "этаж": "этажи",
}
ROADMAP_UNSUPPORTED_METRICS = {
    "plan": "план",
    "fact": "факт",
    "deviation": "отклонение",
}
ROADMAP_AVAILABLE_OPTIONS_TEXT = (
    "- этапы\n"
    "- сроки этапов\n"
    "- итоговый срок\n"
    "- внешние этапы: банк или Росреестр\n"
    "- доступные периоды"
)

ROADMAP_COMPATIBILITY_MESSAGE_TEMPLATE = (
    'В дорожной карте нет показателя "{metric}".\n\n'
    "Для дорожной карты доступны:\n"
    f"{ROADMAP_AVAILABLE_OPTIONS_TEXT}"
)

ROADMAP_ALLOWED_GROUP_BY = {"row_order", "step", "parent_step", "action", "external", "total", "period_month"}


def find_roadmap_unsupported_metric(text: str | None) -> str | None:
    normalized = normalize_search_text(text or "")
    if not normalized:
        return None

    for alias, label in ROADMAP_UNSUPPORTED_METRIC_ALIASES.items():
        if alias in normalized:
            return label
    return None


def find_roadmap_unsupported_frame_metric(frame: QueryFrame) -> str | None:
    for metric in frame.metrics:
        if metric in ROADMAP_UNSUPPORTED_METRICS:
            return ROADMAP_UNSUPPORTED_METRICS[metric]
    return None


def check_roadmap_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    unsupported_group_by = [group_by for group_by in frame.group_by if group_by not in ROADMAP_ALLOWED_GROUP_BY]
    if unsupported_group_by:
        return CompatibilityCheck(
            valid=False,
            error="group_by_not_supported_for_roadmap",
            message=(
                "В дорожной карте нет такой разбивки.\n\n"
                "Для дорожной карты доступны: этапы, сроки этапов, итоговый срок, внешние этапы и периоды."
            ),
        )

    unsupported_metric = find_roadmap_unsupported_frame_metric(frame) or find_roadmap_unsupported_metric(user_text)
    if unsupported_metric is None:
        return CompatibilityCheck(valid=True)

    return CompatibilityCheck(
        valid=False,
        error="metric_not_supported_for_roadmap",
        message=ROADMAP_COMPATIBILITY_MESSAGE_TEMPLATE.format(metric=unsupported_metric),
    )
