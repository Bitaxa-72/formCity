from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSpec:
    unit: str
    group_by: set[str]
    filters: set[str]
    projects: set[str]
    privacy: str = "safe_aggregate"


METRIC_CATALOG: dict[str, dict[str, MetricSpec]] = {
    "summary": {
        "revenue": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month", "quarter", "year", "room_type"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "sold_area": MetricSpec(
            unit="square_meter",
            group_by={"project", "period", "month", "quarter", "year", "room_type"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "deal_count": MetricSpec(
            unit="count",
            group_by={"project", "period", "month", "quarter", "year", "room_type"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
    },
    "sales_report": {
        "revenue": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month", "quarter", "year", "floor", "room_type", "agent", "bank"},
            filters={"project", "period", "room_type", "agent", "bank"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "sold_area": MetricSpec(
            unit="square_meter",
            group_by={"project", "period", "month", "quarter", "year", "floor", "room_type"},
            filters={"project", "period", "room_type"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "deal_count": MetricSpec(
            unit="count",
            group_by={"project", "period", "month", "quarter", "year", "floor", "room_type", "agent", "bank"},
            filters={"project", "period", "room_type", "agent", "bank"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "average_deal_price": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month", "quarter", "year", "room_type"},
            filters={"project", "period", "room_type"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "price_per_square_meter": MetricSpec(
            unit="rub_per_square_meter",
            group_by={"project", "period", "month", "quarter", "year", "floor", "room_type"},
            filters={"project", "period", "room_type"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
    },
    "payment_calendar": {
        "plan": MetricSpec(
            unit="rub",
            group_by={"period", "month", "metric"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky"},
        ),
        "fact": MetricSpec(
            unit="rub",
            group_by={"period", "month", "metric"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky"},
        ),
        "deviation": MetricSpec(
            unit="rub",
            group_by={"period", "month", "metric"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky"},
        ),
        "remaining_amount": MetricSpec(
            unit="rub",
            group_by={"period", "month", "metric"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky"},
        ),
    },
    "agents_report": {
        "deal_count": MetricSpec(
            unit="count",
            group_by={"agent", "project", "period", "month"},
            filters={"project", "period", "agent"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "agent_commission": MetricSpec(
            unit="rub",
            group_by={"agent", "project", "period", "month"},
            filters={"project", "period", "agent"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
    },
    "debt_and_bookings": {
        "debt": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
        "booking_amount": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month"},
            filters={"project", "period"},
            projects={"all", "obvodny_118", "well_moskovsky", "evgenievsky"},
        ),
    },
    "roadmap": {
        "pledge_release_amount": MetricSpec(
            unit="rub",
            group_by={"project", "period", "month"},
            filters={"project", "period"},
            projects={"all", "obvodny_118"},
        ),
    },
}
