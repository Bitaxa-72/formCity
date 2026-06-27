from app.llm.schema import Dimension, GroupBy, Metric, PaymentCalendarView, ReportType


REPORT_TYPE_ALIASES: dict[str, list[str]] = {
    ReportType.SUMMARY.value: ["сводный отчет", "сводка", "общий отчет"],
    ReportType.MODEL.value: ["модель", "финансовая модель"],
    ReportType.PAYMENT_CALENDAR.value: ["платежный календарь", "платежи", "план факт платежей", "отклонение по платежам"],
    ReportType.ROADMAP.value: ["дорожная карта", "roadmap", "роадмап"],
    ReportType.SALES_REPORT.value: ["отчет о продажах", "продажи", "выручка", "сделки", "квадратные метры"],
    ReportType.SALES_PLAN_EXECUTION.value: ["исполнение плана продаж", "план продаж", "выполнение плана продаж"],
    ReportType.AGENTS_REPORT.value: ["отчет по агентам", "агенты", "агентское вознаграждение"],
    ReportType.STOCK_FOR_SALE.value: ["остатки в продаже", "остатки", "склад", "экспозиция"],
    ReportType.DEBT_AND_BOOKINGS.value: ["дз и брони", "дз", "дебиторка", "долги", "брони", "бронирования"],
    ReportType.NON_PROJECT_EXPENSES.value: ["непроектные расходы", "расходы вне проекта", "общие расходы"],
}
from app.llm.rules.summary import RULE as SUMMARY_RULE
from app.llm.rules.model import RULE as MODEL_RULE
from app.llm.rules.non_project_expenses import RULE as NON_PROJECT_EXPENSES_RULE
from app.llm.rules.debt_and_bookings import RULE as DEBT_AND_BOOKINGS_RULE
from app.llm.rules.stock_for_sale import RULE as STOCK_FOR_SALE_RULE
from app.llm.rules.sales_report import RULE as SALES_REPORT_RULE
from app.llm.rules.sales_plan_execution import RULE as SALES_PLAN_EXECUTION_RULE
from app.llm.rules.agents_report import RULE as AGENTS_REPORT_RULE
from app.llm.rules.payment_calendar import RULE as PAYMENT_CALENDAR_RULE
from app.llm.rules.roadmap import RULE as ROADMAP_RULE


REPORT_RULES: dict[str, object] = {
    ReportType.SUMMARY.value: SUMMARY_RULE,
    ReportType.MODEL.value: MODEL_RULE,
    ReportType.NON_PROJECT_EXPENSES.value: NON_PROJECT_EXPENSES_RULE,
    ReportType.DEBT_AND_BOOKINGS.value: DEBT_AND_BOOKINGS_RULE,
    ReportType.STOCK_FOR_SALE.value: STOCK_FOR_SALE_RULE,
    ReportType.SALES_REPORT.value: SALES_REPORT_RULE,
    ReportType.SALES_PLAN_EXECUTION.value: SALES_PLAN_EXECUTION_RULE,
    ReportType.AGENTS_REPORT.value: AGENTS_REPORT_RULE,
    ReportType.PAYMENT_CALENDAR.value: PAYMENT_CALENDAR_RULE,
    ReportType.ROADMAP.value: ROADMAP_RULE,
}
