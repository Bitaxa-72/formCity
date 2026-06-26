from app.reports.common import MetricSpec


PAYMENT_CALENDAR_GROUP_BY = {"project", "period", "month", "metric", "article", "article_kind"}
PAYMENT_CALENDAR_FILTERS = {"project", "period", "metric", "article", "article_kind"}
PAYMENT_CALENDAR_PROJECTS = {"all", "obvodny", "moskovsky"}
PAYMENT_CALENDAR_FULL_METRICS = ["plan", "fact", "deviation"]

PAYMENT_CALENDAR_METRICS = {
    "plan": MetricSpec(
        unit="rub",
        group_by=PAYMENT_CALENDAR_GROUP_BY,
        filters=PAYMENT_CALENDAR_FILTERS,
        projects=PAYMENT_CALENDAR_PROJECTS,
    ),
    "fact": MetricSpec(
        unit="rub",
        group_by=PAYMENT_CALENDAR_GROUP_BY,
        filters=PAYMENT_CALENDAR_FILTERS,
        projects=PAYMENT_CALENDAR_PROJECTS,
    ),
    "deviation": MetricSpec(
        unit="rub",
        group_by=PAYMENT_CALENDAR_GROUP_BY,
        filters=PAYMENT_CALENDAR_FILTERS,
        projects=PAYMENT_CALENDAR_PROJECTS,
    ),
}
