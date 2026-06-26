from app.pipeline.query_frame import QueryFrame
from app.reports.model.catalog import MODEL_SUMMARY_METRICS


def apply_model_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "model":
        return frame

    if frame.view == "model_available_metrics":
        return frame.model_copy(
            update={
                "intent": "dimension_query",
                "project": "obvodny",
                "dimension": "metric",
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.view == "model_available_snapshots":
        return frame.model_copy(
            update={
                "intent": "dimension_query",
                "project": "obvodny",
                "dimension": "snapshot_month",
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
                "project": "obvodny",
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    view = frame.view or ("model_summary" if not frame.metrics else "model_kpi")
    metrics = frame.metrics or MODEL_SUMMARY_METRICS.copy()
    filters = dict(frame.filters)
    filters.setdefault("scenario", "current")
    group_by = [item for item in frame.group_by if item != "project"]

    return frame.model_copy(
        update={
            "project": "obvodny",
            "view": view,
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
