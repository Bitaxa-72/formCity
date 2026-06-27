from app.reports.common import MetricSpec
from app.reports.agents_report.catalog import AGENTS_REPORT_METRICS
from app.reports.agents_report.sql import AGENTS_REPORT_SQL_TEMPLATE
from app.reports.debt_and_bookings.catalog import DEBT_AND_BOOKINGS_METRICS
from app.reports.debt_and_bookings.sql import DEBT_AND_BOOKINGS_SQL_TEMPLATE
from app.reports.model.catalog import MODEL_METRICS
from app.reports.model.sql import MODEL_SQL_TEMPLATE
from app.reports.non_project_expenses.catalog import NON_PROJECT_EXPENSES_METRICS
from app.reports.non_project_expenses.sql import NON_PROJECT_EXPENSES_SQL_TEMPLATE
from app.reports.payment_calendar.catalog import PAYMENT_CALENDAR_METRICS
from app.reports.payment_calendar.sql import PAYMENT_CALENDAR_SQL_TEMPLATE
from app.reports.roadmap.catalog import ROADMAP_METRICS
from app.reports.roadmap.sql import ROADMAP_SQL_TEMPLATE
from app.reports.sales_plan_execution.catalog import SALES_PLAN_EXECUTION_METRICS
from app.reports.sales_plan_execution.sql import SALES_PLAN_EXECUTION_SQL_TEMPLATE
from app.reports.sales_report.catalog import SALES_REPORT_METRICS
from app.reports.sales_report.sql import SALES_REPORT_SQL_TEMPLATE
from app.reports.sql import ReportSQLTemplate
from app.reports.stock_for_sale.catalog import STOCK_FOR_SALE_METRICS
from app.reports.stock_for_sale.sql import STOCK_FOR_SALE_SQL_TEMPLATE
from app.reports.summary.catalog import SUMMARY_METRICS
from app.reports.summary.sql import SUMMARY_SQL_TEMPLATE


METRIC_CATALOG: dict[str, dict[str, MetricSpec]] = {
    "summary": SUMMARY_METRICS,
    "model": MODEL_METRICS,
    "payment_calendar": PAYMENT_CALENDAR_METRICS,
    "roadmap": ROADMAP_METRICS,
    "sales_report": SALES_REPORT_METRICS,
    "sales_plan_execution": SALES_PLAN_EXECUTION_METRICS,
    "agents_report": AGENTS_REPORT_METRICS,
    "stock_for_sale": STOCK_FOR_SALE_METRICS,
    "debt_and_bookings": DEBT_AND_BOOKINGS_METRICS,
    "non_project_expenses": NON_PROJECT_EXPENSES_METRICS,
}

SQL_TEMPLATES: dict[str, ReportSQLTemplate] = {
    "model": MODEL_SQL_TEMPLATE,
    "non_project_expenses": NON_PROJECT_EXPENSES_SQL_TEMPLATE,
    "payment_calendar": PAYMENT_CALENDAR_SQL_TEMPLATE,
    "roadmap": ROADMAP_SQL_TEMPLATE,
    "debt_and_bookings": DEBT_AND_BOOKINGS_SQL_TEMPLATE,
    "stock_for_sale": STOCK_FOR_SALE_SQL_TEMPLATE,
    "sales_report": SALES_REPORT_SQL_TEMPLATE,
    "sales_plan_execution": SALES_PLAN_EXECUTION_SQL_TEMPLATE,
    "agents_report": AGENTS_REPORT_SQL_TEMPLATE,
    "summary": SUMMARY_SQL_TEMPLATE,
}
