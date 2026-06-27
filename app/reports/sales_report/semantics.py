from app.pipeline.query_frame import QueryFrame
from app.reports.sales_report.catalog import SALES_REPORT_SEGMENT_METRICS, SALES_REPORT_SEGMENTS, SALES_REPORT_SUMMARY_METRICS


SALES_REPORT_DEFAULT_PROJECT = "obvodny"

SALES_REPORT_LIST_VIEWS = {
    "sales_available_snapshots": "snapshot_month",
    "sales_available_periods": "period_month",
    "sales_available_segments": "segment",
    "sales_available_metrics": "metric_key",
    "sales_available_owners": "owner_scope",
    "sales_available_scenarios": "scenario",
}

SALES_REPORT_SEGMENT_VIEWS = {
    "sales_apartments": "apartments",
    "sales_commercial_1_floor": "commercial_1_floor",
    "sales_restaurant": "restaurant",
    "sales_storage": "storage",
    "sales_commercial_2_floor": "commercial_2_floor",
    "sales_sh": "sh",
}


def sales_project_update(frame: QueryFrame) -> dict[str, object]:
    notices = list(frame.notices)
    if frame.project and frame.project not in {SALES_REPORT_DEFAULT_PROJECT, "all"}:
        notices.append("Отчет о продажах сейчас загружен только по Обводному, поэтому показываю Обводный.")
    return {
        "project": SALES_REPORT_DEFAULT_PROJECT,
        "notices": notices,
    }


def has_sales_month_filter(filters: dict[str, object]) -> bool:
    return bool(filters.get("period_month"))


def apply_sales_report_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "sales_report":
        return frame

    project_update = sales_project_update(frame)

    if frame.view in SALES_REPORT_LIST_VIEWS:
        filters = dict(frame.filters)
        if frame.view == "sales_available_periods":
            filters["period_kind"] = "month"
        return frame.model_copy(
            update={
                **project_update,
                "intent": "dimension_query",
                "dimension": SALES_REPORT_LIST_VIEWS[frame.view],
                "filters": filters,
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

    if frame.view in SALES_REPORT_SEGMENT_VIEWS:
        filters["segment"] = SALES_REPORT_SEGMENT_VIEWS[frame.view]
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_REPORT_SEGMENT_METRICS.copy()
    elif frame.view == "sales_by_segments":
        filters.setdefault("segment", SALES_REPORT_SEGMENTS.copy())
        filters.setdefault("owner_scope", "all")
        metrics = metrics or SALES_REPORT_SEGMENT_METRICS.copy()
        if "segment" not in group_by:
            group_by.append("segment")
    elif frame.view == "sales_monthly":
        filters["period_kind"] = "month"
        filters.setdefault("owner_scope", "all")
        metrics = metrics or ["sales_contract_revenue"]
        if not group_by:
            group_by = ["period_month", "scenario"]
    elif frame.view == "sales_payments":
        filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")
        metrics = metrics or ["sales_ddu_actual_payments", "sales_ddu_remaining_payment_schedule"]
    elif frame.view == "sales_price_per_sqm":
        filters.setdefault("segment", SALES_REPORT_SEGMENTS.copy())
        filters.setdefault("owner_scope", "all")
        metrics = metrics or ["sales_price_per_sqm", "sales_cumulative_price_per_sqm"]
        if not group_by:
            group_by = ["segment"]
    else:
        metrics = metrics or SALES_REPORT_SUMMARY_METRICS.copy()
        if any(metric in metrics for metric in {"sales_contract_area_sqm", "sales_contract_count", "sales_price_per_sqm", "sales_cumulative_price_per_sqm"}):
            filters.setdefault("segment", SALES_REPORT_SEGMENTS.copy())
            if "segment" not in group_by:
                group_by.append("segment")
        else:
            filters.setdefault("segment", "project_total")
        filters.setdefault("owner_scope", "all")

    if has_sales_month_filter(filters):
        filters["period_kind"] = "month"
        if "scenario" not in filters and "scenario" not in group_by:
            group_by.append("scenario")
    else:
        filters.setdefault("period_kind", "total")
        filters.setdefault("scenario", "total")

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
