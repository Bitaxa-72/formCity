from app.pipeline.query_frame import QueryFrame
from app.reports.model.semantics import apply_model_view
from app.reports.non_project_expenses.semantics import apply_non_project_expenses_view
from app.reports.payment_calendar.semantics import apply_payment_calendar_view
from app.reports.roadmap.semantics import apply_roadmap_view


def apply_report_semantics(frame: QueryFrame) -> QueryFrame:
    if frame.report_type == "model":
        return apply_model_view(frame)
    if frame.report_type == "non_project_expenses":
        return apply_non_project_expenses_view(frame)
    if frame.report_type == "payment_calendar":
        return apply_payment_calendar_view(frame)
    if frame.report_type == "roadmap":
        return apply_roadmap_view(frame)
    return frame
