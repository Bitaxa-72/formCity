from app.pipeline.query_frame import QueryFrame
from app.reports.roadmap.catalog import ROADMAP_FULL_METRICS


ROADMAP_ROW_GROUP_BY = ["row_order", "step", "parent_step", "action", "external", "total"]
ROADMAP_VIEW_FILTERS = {"is_total", "is_external", "action_text_contains"}
ROADMAP_GENERAL_VIEW_FILTERS = ROADMAP_VIEW_FILTERS | {"step_no"}


def apply_roadmap_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "roadmap":
        return frame
    if frame.awaiting_clarification:
        return frame

    if frame.intent == "dimension_query":
        return frame.model_copy(
            update={
                "project": "all",
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    requested_metrics = frame.metrics or []
    view = frame.view
    if view is None and requested_metrics and set(requested_metrics) <= {"duration_min", "duration_max", "duration_range"}:
        view = "total_duration"
    elif view is None and "step_count" in requested_metrics:
        view = "step_count"
    else:
        view = view or "full_roadmap"

    metrics = requested_metrics or ROADMAP_FULL_METRICS.copy()
    filters = dict(frame.filters)
    group_by = list(frame.group_by)
    action_text_contains = filters.get("action_text_contains")

    if view in {"full_roadmap", "roadmap_steps"}:
        for key in ROADMAP_GENERAL_VIEW_FILTERS:
            filters.pop(key, None)
        group_by = ROADMAP_ROW_GROUP_BY.copy()
    elif view == "step_details":
        for key in ROADMAP_VIEW_FILTERS:
            filters.pop(key, None)
        group_by = ROADMAP_ROW_GROUP_BY.copy()
    elif view == "external_steps":
        for key in ROADMAP_VIEW_FILTERS:
            filters.pop(key, None)
        filters["is_external"] = True
        filters["is_total"] = False
        if action_text_contains is not None:
            filters["action_text_contains"] = action_text_contains
        group_by = ROADMAP_ROW_GROUP_BY.copy()
    elif view == "total_duration":
        for key in ROADMAP_GENERAL_VIEW_FILTERS:
            filters.pop(key, None)
        filters["is_total"] = True
        metrics = ["duration_min", "duration_max"]
        group_by = []
    elif view == "step_count":
        for key in ROADMAP_GENERAL_VIEW_FILTERS:
            filters.pop(key, None)
        filters["is_total"] = False
        metrics = ["step_count"]
        group_by = []

    return frame.model_copy(
        update={
            "project": "all",
            "view": view,
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
