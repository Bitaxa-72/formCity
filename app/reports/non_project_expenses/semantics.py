from app.pipeline.query_frame import QueryFrame
from app.reports.non_project_expenses.catalog import NON_PROJECT_EXPENSES_DEFAULT_METRICS


NON_PROJECT_EXPENSES_LIST_VIEWS = {
    "non_project_expenses_available_periods": "period_month",
    "non_project_expenses_available_categories": "fm_category",
    "non_project_expenses_available_items": "item_name",
    "non_project_expenses_available_kinds": "item_kind",
}

NON_PROJECT_EXPENSES_VIEW_FILTERS = {
    "non_project_expenses_details": {"row_type": "detail"},
    "non_project_expenses_summary": {"row_type": "summary"},
}


def apply_non_project_expenses_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "non_project_expenses":
        return frame

    if frame.view in NON_PROJECT_EXPENSES_LIST_VIEWS:
        return frame.model_copy(
            update={
                "intent": "dimension_query",
                "project": "all",
                "dimension": NON_PROJECT_EXPENSES_LIST_VIEWS[frame.view],
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
                "project": "all",
                "metrics": [],
                "group_by": [],
                "ready": True,
                "missing_fields": [],
                "clarification_question": None,
            },
        )

    filters = dict(frame.filters)
    if frame.view in NON_PROJECT_EXPENSES_VIEW_FILTERS:
        filters.update(NON_PROJECT_EXPENSES_VIEW_FILTERS[frame.view])

    metrics = frame.metrics or NON_PROJECT_EXPENSES_DEFAULT_METRICS.copy()
    group_by = [item for item in frame.group_by if item != "project"]
    if not filters and not group_by:
        filters["row_type"] = "detail"
        group_by = ["fm_category"]

    return frame.model_copy(
        update={
            "project": "all",
            "metrics": metrics,
            "filters": filters,
            "group_by": group_by,
            "ready": True,
            "missing_fields": [],
            "clarification_question": None,
        },
    )
