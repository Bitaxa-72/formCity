from app.pipeline.query_frame import QueryFrame, QueryPeriod
from app.reports.summary.catalog import SUMMARY_DEFAULT_METRICS, SUMMARY_RAW_VIEWS, SUMMARY_VALUE_METRICS


SUMMARY_LIST_VIEWS = {
    "summary_available_projects": "project",
    "summary_available_files": "source_file",
    "summary_available_sheets": "sheet_name",
    "summary_available_sheet_kinds": "sheet_kind",
    "summary_available_headers": "header_key",
    "summary_available_row_types": "row_type",
}


def clear_summary_period(frame: QueryFrame) -> QueryPeriod:
    period_data = frame.period.model_dump(by_alias=True)
    period_data["from"] = None
    period_data["to"] = None
    period_data["label"] = "весь доступный объем сводных таблиц"
    return QueryPeriod.model_validate(period_data)


def apply_summary_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "summary":
        return frame

    base_update = {"period": clear_summary_period(frame)}

    if frame.view in SUMMARY_LIST_VIEWS:
        filters = dict(frame.filters)
        dimension = SUMMARY_LIST_VIEWS[frame.view]
        if dimension == "header_key":
            filters["is_sensitive"] = False
        return frame.model_copy(
            update={
                **base_update,
                "intent": "dimension_query",
                "dimension": dimension,
                "filters": filters,
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.intent == "dimension_query":
        filters = dict(frame.filters)
        if frame.dimension == "header_key":
            filters["is_sensitive"] = False
        return frame.model_copy(
            update={
                **base_update,
                "filters": filters,
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    if frame.view in SUMMARY_RAW_VIEWS:
        filters = dict(frame.filters)
        filters["is_sensitive"] = False
        return frame.model_copy(
            update={
                **base_update,
                "metrics": [],
                "filters": filters,
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    filters = dict(frame.filters)
    group_by = list(frame.group_by)
    metrics = list(frame.metrics)

    if frame.view == "summary_values":
        filters["is_sensitive"] = False
        metrics = metrics or SUMMARY_VALUE_METRICS.copy()
        if "header_key" not in filters and not group_by:
            group_by = ["header_key"]
    else:
        metrics = metrics or SUMMARY_DEFAULT_METRICS.copy()

    if (frame.project or "all") == "all" and metrics and "project" not in group_by:
        group_by.insert(0, "project")

    return frame.model_copy(
        update={
            **base_update,
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
