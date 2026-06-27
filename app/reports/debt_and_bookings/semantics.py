from app.pipeline.query_frame import QueryFrame
from app.reports.debt_and_bookings.catalog import (
    DEBT_AND_BOOKINGS_DEFAULT_METRICS,
    DEBT_AND_BOOKINGS_DEVIATION_METRICS,
    DEBT_AND_BOOKINGS_REFUSAL_METRICS,
)


DEBT_AND_BOOKINGS_DEFAULT_PROJECT = "obvodny"

DEBT_AND_BOOKINGS_LIST_VIEWS = {
    "debt_bookings_available_periods": "snapshot_month",
    "debt_bookings_available_kinds": "item_kind",
    "debt_bookings_available_sections": "section",
    "debt_bookings_available_unit_numbers": "unit_number",
    "debt_bookings_available_statuses": "status",
    "debt_bookings_available_payment_types": "payment_type",
}

DEBT_AND_BOOKINGS_KIND_VIEWS = {
    "debt_bookings_bookings": "booking",
    "debt_bookings_overdue": "overdue",
    "debt_bookings_current": "current",
    "debt_bookings_registered": "registered",
}


def debt_project_update(frame: QueryFrame) -> dict[str, object]:
    notices = list(frame.notices)
    if frame.project and frame.project not in {DEBT_AND_BOOKINGS_DEFAULT_PROJECT, "all"}:
        notices.append("Отчет ДЗ и брони сейчас загружен только по Обводному, поэтому показываю Обводный.")
    return {
        "project": DEBT_AND_BOOKINGS_DEFAULT_PROJECT,
        "notices": notices,
    }


def apply_debt_and_bookings_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "debt_and_bookings":
        return frame

    project_update = debt_project_update(frame)

    if frame.view in DEBT_AND_BOOKINGS_LIST_VIEWS:
        dimension = DEBT_AND_BOOKINGS_LIST_VIEWS[frame.view]
        filters = dict(frame.filters)
        if dimension == "unit_number":
            filters["row_type"] = "detail"
            filters["unit_number_not_null"] = True
        if dimension == "status":
            filters["source_kind"] = "refusals"
        if dimension == "payment_type":
            filters["source_kind"] = "refusals"
        return frame.model_copy(
            update={
                **project_update,
                "intent": "dimension_query",
                "dimension": dimension,
                "metrics": [],
                "filters": filters,
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.intent == "dimension_query":
        return frame.model_copy(
            update={
                **project_update,
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    filters = dict(frame.filters)
    group_by = [item for item in frame.group_by if item != "project"]
    metrics = list(frame.metrics)
    if "unit_number" in group_by:
        filters.setdefault("row_type", "detail")
        filters["unit_number_not_null"] = True

    if frame.view in DEBT_AND_BOOKINGS_KIND_VIEWS:
        filters["source_kind"] = "items"
        filters["item_kind"] = DEBT_AND_BOOKINGS_KIND_VIEWS[frame.view]
        metrics = metrics or DEBT_AND_BOOKINGS_DEFAULT_METRICS.copy()
    elif frame.view == "debt_bookings_deviations":
        filters["source_kind"] = "deviations"
        metrics = metrics or DEBT_AND_BOOKINGS_DEVIATION_METRICS.copy()
        if not group_by:
            group_by = ["item_kind"]
    elif frame.view == "debt_bookings_refusals":
        filters["source_kind"] = "refusals"
        metrics = metrics or DEBT_AND_BOOKINGS_REFUSAL_METRICS.copy()
        if not group_by:
            group_by = ["status"]
    elif frame.view == "debt_bookings_monthly":
        filters["source_kind"] = "monthly"
        metrics = metrics or ["debt_monthly_value"]
        if not group_by:
            group_by = ["period_month", "item_kind"]
    else:
        filters.setdefault("source_kind", "items")
        metrics = metrics or DEBT_AND_BOOKINGS_DEFAULT_METRICS.copy()
        if not group_by:
            group_by = ["item_kind"]

    return frame.model_copy(
        update={
            **project_update,
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
