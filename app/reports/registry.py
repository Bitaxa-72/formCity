from app.reports.common import MetricSpec
from app.reports.model.catalog import MODEL_METRICS
from app.reports.model.sql import MODEL_SQL_TEMPLATE
from app.reports.non_project_expenses.catalog import NON_PROJECT_EXPENSES_METRICS
from app.reports.non_project_expenses.sql import NON_PROJECT_EXPENSES_SQL_TEMPLATE
from app.reports.payment_calendar.catalog import PAYMENT_CALENDAR_METRICS
from app.reports.payment_calendar.sql import PAYMENT_CALENDAR_SQL_TEMPLATE
from app.reports.roadmap.catalog import ROADMAP_METRICS
from app.reports.roadmap.sql import ROADMAP_SQL_TEMPLATE
from app.reports.sql import ReportSQLTemplate


METRIC_CATALOG: dict[str, dict[str, MetricSpec]] = {
    "summary": {},
    "model": MODEL_METRICS,
    "payment_calendar": PAYMENT_CALENDAR_METRICS,
    "roadmap": ROADMAP_METRICS,
    "sales_report": {},
    "sales_plan_execution": {},
    "agents_report": {},
    "stock_for_sale": {},
    "debt_and_bookings": {},
    "non_project_expenses": NON_PROJECT_EXPENSES_METRICS,
}

SQL_TEMPLATES: dict[str, ReportSQLTemplate] = {
    "model": MODEL_SQL_TEMPLATE,
    "non_project_expenses": NON_PROJECT_EXPENSES_SQL_TEMPLATE,
    "payment_calendar": PAYMENT_CALENDAR_SQL_TEMPLATE,
    "roadmap": ROADMAP_SQL_TEMPLATE,
}
