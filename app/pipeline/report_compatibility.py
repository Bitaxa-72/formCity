from app.pipeline.query_frame import QueryFrame
from app.reports.model.compatibility import check_model_compatibility
from app.reports.common import CompatibilityCheck
from app.reports.non_project_expenses.compatibility import check_non_project_expenses_compatibility
from app.reports.payment_calendar.compatibility import (
    PAYMENT_CALENDAR_COMPATIBILITY_MESSAGE_TEMPLATE,
    PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE,
    PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES,
    check_payment_calendar_compatibility,
)
from app.reports.roadmap.compatibility import check_roadmap_compatibility


def check_report_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    if frame.report_type == "model":
        return check_model_compatibility(frame, user_text)
    if frame.report_type == "non_project_expenses":
        return check_non_project_expenses_compatibility(frame, user_text)
    if frame.report_type == "payment_calendar":
        return check_payment_calendar_compatibility(frame, user_text)
    if frame.report_type == "roadmap":
        return check_roadmap_compatibility(frame, user_text)
    return CompatibilityCheck(valid=True)
