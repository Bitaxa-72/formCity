from app.pipeline.query_frame import QueryFrame
from app.reports.model.catalog import MODEL_RAW_VIEWS, MODEL_SUMMARY_METRICS


PROJECT_LABELS = {
    "all": "всех проектов",
    "moskovsky": "Московского",
    "evgenievsky": "Евгеньевского",
}
MODEL_DEFAULT_PROJECT = "obvodny"


def model_project_update(frame: QueryFrame) -> dict[str, object]:
    requested_project = frame.project
    notices = list(frame.notices)
    if requested_project and requested_project not in {MODEL_DEFAULT_PROJECT, "all"}:
        label = PROJECT_LABELS.get(requested_project, requested_project)
        notices.append(f"Финансовая модель сейчас загружена только по Обводному, поэтому показываю Обводный вместо {label}.")
    return {
        "project": MODEL_DEFAULT_PROJECT,
        "notices": notices,
    }


def apply_model_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "model":
        return frame

    project_update = model_project_update(frame)

    if frame.view == "model_available_metrics":
        return frame.model_copy(
            update={
                "intent": "dimension_query",
                **project_update,
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
                **project_update,
                "dimension": "snapshot_month",
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.view == "model_raw_sheets":
        return frame.model_copy(
            update={
                "intent": "dimension_query",
                **project_update,
                "dimension": "raw_sheet",
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.intent == "dimension_query" and frame.dimension == "raw_sheet":
        return frame.model_copy(
            update={
                "view": "model_raw_sheets",
                **project_update,
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.view in MODEL_RAW_VIEWS:
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

    view = frame.view or ("model_summary" if not frame.metrics else "model_kpi")
    metrics = frame.metrics or MODEL_SUMMARY_METRICS.copy()
    filters = dict(frame.filters)
    filters.setdefault("scenario", "current")
    group_by = [item for item in frame.group_by if item != "project"]

    return frame.model_copy(
        update={
            **project_update,
            "view": view,
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
