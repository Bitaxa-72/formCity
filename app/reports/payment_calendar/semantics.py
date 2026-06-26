from dataclasses import dataclass

from app.pipeline.query_frame import QueryFrame
from app.reports.payment_calendar.catalog import PAYMENT_CALENDAR_FULL_METRICS


@dataclass(frozen=True)
class PaymentCalendarViewRule:
    article_kinds: list[str]
    grouped_by_article_kind: bool = False
    grouped_by_article: bool = False


PAYMENT_CALENDAR_VIEW_RULES = {
    "summary": PaymentCalendarViewRule(
        article_kinds=["balance_start", "income_total", "payment_total", "balance_end"],
        grouped_by_article_kind=True,
    ),
    "details": PaymentCalendarViewRule(
        article_kinds=["detail"],
        grouped_by_article=True,
    ),
    "payments": PaymentCalendarViewRule(article_kinds=["payment_total"]),
    "income": PaymentCalendarViewRule(article_kinds=["income_total"]),
    "balance_start": PaymentCalendarViewRule(article_kinds=["balance_start"]),
    "balance_end": PaymentCalendarViewRule(article_kinds=["balance_end"]),
}


def build_payment_calendar_group_by(frame: QueryFrame, rule: PaymentCalendarViewRule) -> list[str]:
    group_by = []
    if frame.project == "all":
        group_by.append("project")
    if rule.grouped_by_article_kind:
        group_by.append("article_kind")
    if rule.grouped_by_article:
        group_by.append("article")
    return group_by


def apply_payment_calendar_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "payment_calendar" or not frame.view:
        return frame
    if frame.filters.get("article"):
        return frame

    rule = PAYMENT_CALENDAR_VIEW_RULES.get(frame.view)
    if rule is None:
        return frame

    filters = dict(frame.filters)
    filters["article_kind"] = rule.article_kinds
    return frame.model_copy(
        update={
            "metrics": frame.metrics or PAYMENT_CALENDAR_FULL_METRICS.copy(),
            "filters": filters,
            "group_by": build_payment_calendar_group_by(frame, rule),
        },
    )
