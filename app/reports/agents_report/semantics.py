from app.pipeline.query_frame import QueryFrame
from app.reports.agents_report.catalog import AGENTS_REPORT_DDU_METRICS, AGENTS_REPORT_DEFAULT_METRICS


AGENTS_REPORT_DEFAULT_PROJECT = "obvodny"

AGENTS_REPORT_LIST_VIEWS = {
    "agents_available_snapshots": "snapshot_month",
    "agents_available_budget_months": "budget_month",
    "agents_available_payment_months": "payment_period_month",
    "agents_available_value_kinds": "value_kind",
}


def agents_project_update(frame: QueryFrame) -> dict[str, object]:
    notices = list(frame.notices)
    if frame.project and frame.project not in {AGENTS_REPORT_DEFAULT_PROJECT, "all"}:
        notices.append("Отчет по агентам сейчас загружен только по Обводному, поэтому показываю Обводный.")
    return {
        "project": AGENTS_REPORT_DEFAULT_PROJECT,
        "notices": notices,
    }


def apply_agents_report_view(frame: QueryFrame) -> QueryFrame:
    if frame.report_type != "agents_report":
        return frame

    project_update = agents_project_update(frame)

    if frame.view in AGENTS_REPORT_LIST_VIEWS:
        filters = dict(frame.filters)
        dimension = AGENTS_REPORT_LIST_VIEWS[frame.view]
        if dimension in {"payment_period_month", "value_kind"}:
            filters["source_kind"] = "monthly"
        if dimension == "budget_month":
            filters["source_kind"] = "deals"
        return frame.model_copy(
            update={
                **project_update,
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

    if frame.view == "agents_monthly":
        filters["source_kind"] = "monthly"
        metrics = metrics or ["agents_monthly_value"]
        if not group_by:
            group_by = ["payment_period_month", "value_kind"]
    elif frame.view == "agents_by_budget_month":
        filters["source_kind"] = "deals"
        metrics = metrics or AGENTS_REPORT_DEFAULT_METRICS.copy()
        if not group_by:
            group_by = ["budget_month"]
    elif frame.view == "agents_ddu":
        filters["source_kind"] = "deals"
        metrics = metrics or AGENTS_REPORT_DDU_METRICS.copy()
    else:
        filters["source_kind"] = "deals"
        metrics = metrics or AGENTS_REPORT_DEFAULT_METRICS.copy()

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
