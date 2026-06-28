from app.pipeline.query_frame import QueryFrame
from app.pipeline.semantic_compatibility import check_semantic_compatibility
from app.reports.agents_report.compatibility import check_agents_report_compatibility
from app.reports.debt_and_bookings.compatibility import check_debt_and_bookings_compatibility
from app.reports.model.compatibility import check_model_compatibility
from app.reports.common import CompatibilityCheck
from app.reports.non_project_expenses.compatibility import check_non_project_expenses_compatibility
from app.reports.payment_calendar.compatibility import (
    PAYMENT_CALENDAR_COMPATIBILITY_MESSAGE_TEMPLATE,
    PAYMENT_CALENDAR_GROUP_BY_COMPATIBILITY_MESSAGE_TEMPLATE,
    PAYMENT_CALENDAR_UNSUPPORTED_METRIC_ALIASES,
    build_payment_calendar_compatibility_message,
    check_payment_calendar_compatibility,
)
from app.reports.roadmap.compatibility import check_roadmap_compatibility
from app.reports.sales_plan_execution.compatibility import check_sales_plan_execution_compatibility
from app.reports.sales_report.compatibility import check_sales_report_compatibility
from app.reports.stock_for_sale.compatibility import check_stock_for_sale_compatibility
from app.reports.summary.compatibility import check_summary_compatibility


def check_report_compatibility(frame: QueryFrame, user_text: str | None) -> CompatibilityCheck:
    if frame.report_type == "model":
        report_check = check_model_compatibility(frame, user_text)
    elif frame.report_type == "non_project_expenses":
        report_check = check_non_project_expenses_compatibility(frame, user_text)
    elif frame.report_type == "payment_calendar":
        report_check = check_payment_calendar_compatibility(frame, user_text)
    elif frame.report_type == "roadmap":
        report_check = check_roadmap_compatibility(frame, user_text)
    elif frame.report_type == "debt_and_bookings":
        report_check = check_debt_and_bookings_compatibility(frame, user_text)
    elif frame.report_type == "stock_for_sale":
        report_check = check_stock_for_sale_compatibility(frame, user_text)
    elif frame.report_type == "sales_report":
        report_check = check_sales_report_compatibility(frame, user_text)
    elif frame.report_type == "sales_plan_execution":
        report_check = check_sales_plan_execution_compatibility(frame, user_text)
    elif frame.report_type == "agents_report":
        report_check = check_agents_report_compatibility(frame, user_text)
    elif frame.report_type == "summary":
        report_check = check_summary_compatibility(frame, user_text)
    else:
        report_check = CompatibilityCheck(valid=True)

    if not report_check.valid:
        return report_check

    semantic_check = check_semantic_compatibility(frame, user_text)
    if not semantic_check.valid:
        return semantic_check
    return report_check
