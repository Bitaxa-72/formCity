from app.pipeline.query_frame import QueryFrame
from app.reports.sales_plan_execution.catalog import (
    SALES_PLAN_EXECUTION_SEGMENT_METRICS,
    SALES_PLAN_EXECUTION_SUMMARY_METRICS,
)


SALES_PLAN_EXECUTION_DEFAULT_PROJECT = "obvodny"
SALES_PLAN_EXECUTION_LIST_VIEWS = {
    "sales_plan_available_snapshots": "snapshot_month",
    "sales_plan_available_segments": "segment",
    "sales_plan_available_metrics": "metric_key",
    "sales_plan_available_scenarios": "scenario",
    "sales_plan_available_blocks": "block_kind",
}
SALES_PLAN_EXECUTION_SEGMENT_VIEWS = {
    "sales_plan_apartments": "apartments",
    "sales_plan_restaurant": "restaurant",
}


def sales_plan_project_update(frame: QueryFrame) -> dict[str, object]:
    notices = list(frame.notices)
    if frame.project and frame.project not in {SALES_PLAN_EXECUTION_DEFAULT_PROJECT, "all"}:
        notices.append("Отчет об исполнении плана продаж сейчас загружен только по Обводному, поэтому показываю Обводный.")
    return {
        "project": SALES_PLAN_EXECUTION_DEFAULT_PROJECT,
        "notices": notices,
    }


def apply_sales_plan_execution_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "sales_plan_execution":
        return frame

    project_update = sales_plan_project_update(frame)

    if frame.view in SALES_PLAN_EXECUTION_LIST_VIEWS:
        return frame.model_copy(
            update={
                **project_update,
                "intent": "dimension_query",
                "dimension": SALES_PLAN_EXECUTION_LIST_VIEWS[frame.view],
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

    if frame.view in SALES_PLAN_EXECUTION_SEGMENT_VIEWS:
        filters["block_kind"] = "segment_cumulative"
        filters["segment"] = SALES_PLAN_EXECUTION_SEGMENT_VIEWS[frame.view]
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SEGMENT_METRICS.copy()
    elif frame.view == "sales_plan_by_segments":
        filters["block_kind"] = "segment_cumulative"
        filters.setdefault("segment", ["apartments", "restaurant"])
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SEGMENT_METRICS.copy()
        if "segment" not in group_by:
            group_by.append("segment")
    elif frame.view == "sales_plan_month":
        filters["block_kind"] = "month"
        filters["period_kind"] = "month"
        filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SUMMARY_METRICS.copy()
        if "scenario" not in filters and "scenario" not in group_by:
            group_by.append("scenario")
    elif frame.view == "sales_plan_year":
        filters["block_kind"] = "year"
        filters["period_kind"] = "year"
        filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SUMMARY_METRICS.copy()
        if "scenario" not in filters and "scenario" not in group_by:
            group_by.append("scenario")
    elif frame.view == "sales_plan_lifetime":
        filters["block_kind"] = "project_lifetime"
        filters["period_kind"] = "project_total"
        filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SUMMARY_METRICS.copy()
        if "scenario" not in filters and "scenario" not in group_by:
            group_by.append("scenario")
    elif frame.view == "sales_plan_price_per_sqm":
        filters["block_kind"] = "segment_cumulative"
        filters.setdefault("segment", ["apartments", "restaurant"])
        filters.setdefault("owner_scope", "all")
        metrics = metrics or ["sales_plan_price_per_sqm"]
        if "segment" not in group_by:
            group_by.append("segment")
    else:
        filters.setdefault("block_kind", "segment_cumulative")
        filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_PLAN_EXECUTION_SUMMARY_METRICS.copy()
        if "scenario" not in filters and "scenario" not in group_by:
            group_by.append("scenario")

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
