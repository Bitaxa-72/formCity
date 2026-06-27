from app.pipeline.query_frame import QueryFrame
from app.reports.agents_report.semantics import apply_agents_report_view
from app.reports.debt_and_bookings.semantics import apply_debt_and_bookings_view
from app.reports.model.semantics import apply_model_view
from app.reports.non_project_expenses.semantics import apply_non_project_expenses_view
from app.reports.payment_calendar.semantics import apply_payment_calendar_view
from app.reports.roadmap.semantics import apply_roadmap_view
from app.reports.sales_plan_execution.semantics import apply_sales_plan_execution_view
from app.reports.sales_report.semantics import apply_sales_report_view
from app.reports.stock_for_sale.semantics import apply_stock_for_sale_view
from app.reports.summary.semantics import apply_summary_view


def apply_report_semantics(frame: QueryFrame) -> QueryFrame:
    if frame.report_type == "model":
        return apply_model_view(frame)
    if frame.report_type == "non_project_expenses":
        return apply_non_project_expenses_view(frame)
    if frame.report_type == "payment_calendar":
        return apply_payment_calendar_view(frame)
    if frame.report_type == "roadmap":
        return apply_roadmap_view(frame)
    if frame.report_type == "debt_and_bookings":
        return apply_debt_and_bookings_view(frame)
    if frame.report_type == "stock_for_sale":
        return apply_stock_for_sale_view(frame)
    if frame.report_type == "sales_report":
        return apply_sales_report_view(frame)
    if frame.report_type == "sales_plan_execution":
        return apply_sales_plan_execution_view(frame)
    if frame.report_type == "agents_report":
        return apply_agents_report_view(frame)
    if frame.report_type == "summary":
        return apply_summary_view(frame)
    return frame
