from app.pipeline.query_frame import QueryFrame
from app.reports.roadmap.catalog import ROADMAP_FULL_METRICS


ROADMAP_ROW_GROUP_BY = ["row_order", "step", "parent_step", "action", "external", "total"]


def apply_roadmap_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "roadmap":
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

    if view in {"full_roadmap", "roadmap_steps", "step_details"}:
        group_by = ROADMAP_ROW_GROUP_BY.copy()
    elif view == "external_steps":
        filters["is_external"] = True
        filters["is_total"] = False
        group_by = ROADMAP_ROW_GROUP_BY.copy()
    elif view == "total_duration":
        filters["is_total"] = True
        metrics = ["duration_min", "duration_max"]
        group_by = []
    elif view == "step_count":
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
