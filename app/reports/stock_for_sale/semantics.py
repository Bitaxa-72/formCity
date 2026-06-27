from app.pipeline.query_frame import QueryFrame
from app.reports.stock_for_sale.catalog import (
    STOCK_FOR_SALE_AMOUNT_METRICS,
    STOCK_FOR_SALE_DEFAULT_METRICS,
    STOCK_FOR_SALE_PRICE_METRICS,
)


STOCK_FOR_SALE_DEFAULT_PROJECT = "obvodny"

STOCK_FOR_SALE_LIST_VIEWS = {
    "stock_available_periods": "snapshot_month",
    "stock_available_property_types": "property_type",
    "stock_available_row_types": "row_type",
    "stock_available_floors": "floor_number",
}

STOCK_FOR_SALE_PROPERTY_VIEWS = {
    "stock_apartments": "apartment",
    "stock_storage": "storage",
    "stock_restaurants": "restaurant",
    "stock_first_floor": "first_floor",
    "stock_developer_balance": "developer_balance",
}


def stock_project_update(frame: QueryFrame) -> dict[str, object]:
    notices = list(frame.notices)
    if frame.project and frame.project not in {STOCK_FOR_SALE_DEFAULT_PROJECT, "all"}:
        notices.append("Остатки в продаже сейчас загружены только по Обводному, поэтому показываю Обводный.")
    return {
        "project": STOCK_FOR_SALE_DEFAULT_PROJECT,
        "notices": notices,
    }


def apply_stock_for_sale_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "stock_for_sale":
        return frame

    project_update = stock_project_update(frame)

    if frame.view in STOCK_FOR_SALE_LIST_VIEWS:
        return frame.model_copy(
            update={
                **project_update,
                "intent": "dimension_query",
                "dimension": STOCK_FOR_SALE_LIST_VIEWS[frame.view],
                "metrics": [],
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

    if frame.view in STOCK_FOR_SALE_PROPERTY_VIEWS:
        filters["property_type"] = STOCK_FOR_SALE_PROPERTY_VIEWS[frame.view]
        filters.setdefault("row_type", "category")
        metrics = metrics or STOCK_FOR_SALE_DEFAULT_METRICS.copy()
    elif frame.view == "stock_by_floors":
        filters["row_type"] = "detail"
        metrics = metrics or STOCK_FOR_SALE_DEFAULT_METRICS.copy()
        if not group_by:
            group_by = ["floor_number"]
    elif frame.view == "stock_in_work":
        filters["is_in_work"] = True
        filters["row_type"] = "detail"
        metrics = metrics or STOCK_FOR_SALE_DEFAULT_METRICS.copy()
        if not group_by:
            group_by = ["row_label"]
    elif frame.view == "stock_price_per_sqm":
        filters.setdefault("row_type", "total")
        metrics = metrics or STOCK_FOR_SALE_PRICE_METRICS.copy()
    elif frame.view == "stock_amounts":
        filters.setdefault("row_type", "total")
        metrics = metrics or STOCK_FOR_SALE_AMOUNT_METRICS.copy()
    elif frame.view == "stock_details":
        filters["row_type"] = "detail"
        metrics = metrics or STOCK_FOR_SALE_DEFAULT_METRICS.copy()
        if not group_by:
            group_by = ["row_label"]
    else:
        filters.setdefault("row_type", "total")
        metrics = metrics or STOCK_FOR_SALE_DEFAULT_METRICS.copy()

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
